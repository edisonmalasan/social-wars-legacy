/**
 * The **Original art** gallery: a small, honest window onto the clean-room
 * generator in `@swl/art`.
 *
 * The marks are not fetched and are not copied from the original game. They
 * are produced at render time by the same pure, seeded generator that writes
 * `assets/original/`, serialised straight into `data:image/svg+xml` URLs. The
 * licence and the original-work statement come from the generator's own
 * version module, so the notice travels with the artwork it describes.
 *
 * This module owns no game state, sends no command and changes no server
 * authority: it is a reading of a deterministic generator, nothing more. It
 * is JSX-free so Node's native TypeScript stripper can load it in the test
 * suite; `React.createElement` is used directly instead of a JSX transform.
 */
import * as React from 'react';

import type { DialogContent } from '@swl/client';
import {
  buildIcons,
  CC0_NOTICE,
  GENERATOR_NAME,
  GENERATOR_VERSION,
  LICENCE,
  MOTIFS,
  ORIGINAL_WORK_STATEMENT,
} from '@swl/art/browser';

/** The one dialog's id for the gallery. */
export const ORIGINAL_ART_DIALOG_ID = 'original-art';

/** The heading shown in the dialog and on the launcher. */
export const ORIGINAL_ART_TITLE = 'Original art';

/** How many motifs the compact gallery shows at once. */
export const ORIGINAL_ART_MARK_LIMIT = 8;

/** The client's own words — never a value read from the network. */
export const ORIGINAL_ART_INTRO =
  'Clean-room SVG motifs generated here, in the browser, by the same seeded ' +
  'generator that writes assets/original. Nothing is downloaded.';

/** The visible, short CC0 line, derived from the generator's constants. */
export const ORIGINAL_ART_CC0_LINE =
  `${LICENCE} · ${GENERATOR_NAME} ${GENERATOR_VERSION} · original work, dedicated to the public domain.`;

/** The one dialog's descriptor for the gallery. */
export function originalArtDialog(): DialogContent {
  return { id: ORIGINAL_ART_DIALOG_ID, kind: 'alert', title: ORIGINAL_ART_TITLE };
}

/** Encode generated SVG bytes as an inline image source. No file is read. */
export function svgDataUrl(svg: string): string {
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

/** One generated mark, paired with the generator's own metadata. */
export interface OriginalArtMark {
  readonly id: string;
  readonly title: string;
  readonly description: string;
  /** The generator's output path, kept for provenance; never used as a URL. */
  readonly path: string;
  /** An inline data URL; the only value ever handed to an `img` source. */
  readonly src: string;
}

/**
 * Build the gallery's marks from the generator's in-memory artefacts.
 *
 * The list is a pure function of `buildIcons()`: same generator, same marks,
 * same order. The sprite sheet is skipped because it is a composition of the
 * motifs rather than a motif itself. The metadata is looked up by the id in
 * the generated path, so a renamed motif cannot be silently mislabelled.
 */
export function originalArtMarks(): readonly OriginalArtMark[] {
  const decoder = new TextDecoder();
  const marks: OriginalArtMark[] = [];
  for (const file of buildIcons()) {
    if (!file.path.startsWith('icons/') || !file.path.endsWith('.svg')) continue;
    if (file.path === 'icons/sprite-sheet.svg') continue;
    const id = file.path.slice('icons/'.length, -'.svg'.length);
    const motif = MOTIFS.find((entry) => entry.id === id);
    marks.push({
      id,
      title: motif?.title ?? id,
      description: motif?.description ?? '',
      path: file.path,
      src: svgDataUrl(decoder.decode(file.bytes)),
    });
  }
  return marks;
}

/** Build a React element without JSX, so the file is loadable by Node. */
const e = React.createElement;

/**
 * The chrome launcher. It only publishes an open gesture; the gallery it
 * opens is a fresh reading of the generator every time it is drawn.
 */
export function OriginalArtLauncher({
  onOpen,
}: {
  readonly onOpen: () => void;
}): React.JSX.Element {
  return e(
    'button',
    {
      className: 'swl-original-art-launcher',
      type: 'button',
      onClick: onOpen,
      'data-swl-original-art': 'launcher',
      'aria-label': ORIGINAL_ART_TITLE,
    },
    ORIGINAL_ART_TITLE,
    e('span', { className: 'swl-original-art-launcher-count' }, String(MOTIFS.length)),
  );
}

/**
 * The gallery body hosted by the one shared dialog. Every `img` source is a
 * data URL produced above; there is no external asset, copied art or Flash
 * dependency anywhere in this subtree.
 */
export function OriginalArtGallery({
  onClose,
}: {
  readonly onClose: () => void;
}): React.JSX.Element {
  const marks = originalArtMarks();
  const shown = marks.slice(0, ORIGINAL_ART_MARK_LIMIT);
  return e(
    'section',
    { className: 'swl-original-art', 'data-swl-original-art': 'gallery' },
    e('h3', { className: 'swl-original-art-heading' }, ORIGINAL_ART_TITLE),
    e('p', { className: 'swl-original-art-intro' }, ORIGINAL_ART_INTRO),
    e(
      'ul',
      { className: 'swl-original-art-grid' },
      ...shown.map((mark) =>
        e(
          'li',
          {
            key: mark.id,
            className: 'swl-original-art-mark',
            'data-swl-art-id': mark.id,
          },
          e('img', {
            className: 'swl-original-art-img',
            src: mark.src,
            alt: mark.title,
            title: mark.description,
            width: 64,
            height: 64,
            'data-swl-art-generated': 'true',
          }),
          e('span', { className: 'swl-original-art-name' }, mark.title),
        ),
      ),
    ),
    e(
      'p',
      { className: 'swl-original-art-caption' },
      `Showing ${shown.length} of ${marks.length} Foundry motifs. ` +
        'Each is drawn from integer geometry by its own seeded stream.',
    ),
    e(
      'p',
      {
        className: 'swl-original-art-licence',
        'data-swl-art-licence': LICENCE,
      },
      ORIGINAL_ART_CC0_LINE,
    ),
    e(
      'details',
      { className: 'swl-original-art-details' },
      e('summary', null, 'Provenance and licence'),
      e('pre', { className: 'swl-original-art-notice' }, CC0_NOTICE),
      e('p', { className: 'swl-original-art-statement' }, ORIGINAL_WORK_STATEMENT),
    ),
    e(
      'button',
      {
        className: 'swl-original-art-close',
        type: 'button',
        onClick: onClose,
        'data-swl-original-art': 'close',
      },
      'Close',
    ),
  );
}
