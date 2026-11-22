/**
 * The extended portrait popup, the icon-panel layout and the assault portraits.
 *
 * These are the rendered counterparts of three GUI classes. Every value they
 * draw comes from a server view bridged by `state.ts`: the army the server's
 * save accounts for, its last assault receipt and its eight-slot wallet. The
 * client owns no portrait, no icon, no count, no outcome and no command here:
 * absent or malformed server values produce an explicit empty state.
 *
 * Every shape, colour and path below is original geometry authored in this
 * file. There is no image, raster, atlas or external reference of any kind,
 * and no new dependency. The module is JSX-free so Node's native TypeScript
 * stripper can load it in tests.
 */
import * as React from 'react';

import type { DialogContent } from '@swl/client';

import type {
  AssaultPortraitPanelView,
  ExtendedPortraitPopupView,
  IconPanelView,
} from './state.ts';

/** The one dialog's id for the portrait-backed popup. */
export const PORTRAIT_DIALOG_ID = 'portrait-extended';

/** The one dialog's descriptor for the portrait-backed popup. */
export function portraitDialog(): DialogContent {
  return { id: PORTRAIT_DIALOG_ID, kind: 'alert', title: 'Unit portrait' };
}

/** Captions are the client's own words, never a server-written value. */
export const NO_PORTRAIT_CAPTION = 'The server has not published a unit portrait.';
export const NO_ICONS_CAPTION = 'The server has not published resource amounts.';
export const NO_ASSAULT_PORTRAITS_CAPTION = 'The server has not published an assault army.';

/* Original geometry only. The palette is indexed deterministically by the
 * server's item id; there is no roll and no asset lookup. */
const PALETTE = [
  { frame: '#2f4a63', field: '#eef4f8', body: '#4a7d9e', trim: '#c9962f' },
  { frame: '#4d3b63', field: '#f5eef9', body: '#755b96', trim: '#c9962f' },
  { frame: '#315446', field: '#edf6f0', body: '#4c8b70', trim: '#c9962f' },
  { frame: '#634036', field: '#f9efea', body: '#a1644d', trim: '#c9962f' },
] as const;

function paletteFor(itemId: number) {
  const index = ((itemId % PALETTE.length) + PALETTE.length) % PALETTE.length;
  return PALETTE[index] ?? PALETTE[0]!;
}

/** Build a React element without JSX, so the file is loadable by Node's stripper. */
const e = React.createElement;

/**
 * One original framed figure. The id only selects a palette; the state only
 * adds a mark. Nothing here reads an asset or decides a game outcome.
 */
function PortraitFigure({
  itemId,
  state,
}: {
  readonly itemId: number;
  readonly state: 'extended' | 'won' | 'lost' | 'unsettled';
}): React.JSX.Element {
  const palette = paletteFor(itemId);
  return e(
    'svg',
    {
      className: 'swl-portrait-figure',
      viewBox: '0 0 80 96',
      role: 'img',
      'aria-hidden': 'true',
      'data-swl-figure': state,
    },
    e('title', null, 'Original portrait geometry'),
    // Hexagonal frame and field — authored here, not a copied sprite.
    e('path', {
      d: 'M40 3 L74 22 L74 70 L40 91 L6 70 L6 22 Z',
      fill: palette.frame,
      stroke: palette.trim,
      strokeWidth: 2,
    }),
    e('path', {
      d: 'M40 10 L67 26 L67 67 L40 83 L13 67 L13 26 Z',
      fill: palette.field,
    }),
    // A stylised original figure: shoulders, head and a simple face.
    e('path', { d: 'M18 69 C20 50 30 44 40 44 C50 44 60 50 62 69 Z', fill: palette.body }),
    e('circle', { cx: 40, cy: 33, r: 12, fill: palette.body, stroke: palette.frame, strokeWidth: 2 }),
    e('path', { d: 'M33 32 h5 M42 32 h5', stroke: palette.field, strokeWidth: 2, fill: 'none' }),
    e('path', { d: 'M36 39 Q40 43 44 39', stroke: palette.field, strokeWidth: 1.5, fill: 'none' }),
    state === 'extended'
      ? e('path', {
          d: 'M40 5 L44 12 L40 19 L36 12 Z',
          fill: palette.trim,
          'data-swl-figure-mark': 'extended',
        })
      : null,
    state === 'won' || state === 'lost'
      ? e('path', {
          d: state === 'won' ? 'M30 76 l7 7 l14 -16' : 'M31 75 l18 16 M49 75 l-18 16',
          fill: 'none',
          stroke: state === 'won' ? '#2f7a4f' : '#b3473a',
          strokeWidth: 4,
          strokeLinecap: 'round',
          'data-swl-figure-mark': state,
        })
      : null,
  );
}

/**
 * The extended portrait popup's launcher: a button around the one portrait the
 * server accounts for. With no server unit it draws an explicit empty state
 * and no button, so no portrait, name or count is invented.
 */
export function ExtendedPortraitButton({
  view,
  onOpen,
}: {
  readonly view: ExtendedPortraitPopupView | null;
  readonly onOpen?: () => void;
}): React.JSX.Element {
  if (!view) {
    return e(
      'div',
      { className: 'swl-portrait-launcher-empty', 'data-swl-portrait-popup': 'empty' },
      NO_PORTRAIT_CAPTION,
    );
  }
  return e(
    'button',
    {
      type: 'button',
      className: 'swl-portrait-launcher',
      'data-swl-portrait-popup': 'open',
      'data-swl-unit-id': view.itemId,
      'data-swl-portrait-count': view.count,
      disabled: !onOpen,
      onClick: onOpen,
    },
    e(PortraitFigure, { itemId: view.itemId, state: 'extended' }),
    e(
      'span',
      { className: 'swl-portrait-launcher-name', 'data-swl-portrait-name': '' },
      view.name ?? `Unit ${view.itemId}`,
    ),
    e(
      'span',
      { className: 'swl-portrait-launcher-count', 'data-swl-portrait-count-text': '' },
      `×${view.count}`,
    ),
  );
}

/** The portrait-backed body hosted by the one shared dialog. */
export function PortraitPopupBody({
  view,
  onClose,
}: {
  readonly view: ExtendedPortraitPopupView | null;
  readonly onClose: () => void;
}): React.JSX.Element {
  if (!view) {
    return e(
      'div',
      { className: 'swl-portrait-popup', role: 'status', 'data-swl-portrait-body': 'empty' },
      e('p', { className: 'swl-portrait-popup-note' }, NO_PORTRAIT_CAPTION),
      e('button', { type: 'button', onClick: onClose }, 'Close'),
    );
  }
  return e(
    'div',
    { className: 'swl-portrait-popup', role: 'status', 'data-swl-portrait-body': 'unit' },
    e(PortraitFigure, { itemId: view.itemId, state: 'extended' }),
    e('p', { className: 'swl-portrait-popup-name', 'data-swl-unit-id': view.itemId }, view.name ?? `Unit ${view.itemId}`),
    e('p', { className: 'swl-portrait-popup-count', 'data-swl-portrait-count': view.count }, `×${view.count}`),
    e('p', { className: 'swl-portrait-popup-level', 'data-swl-portrait-level': view.level }, `Level ${view.level}`),
    e('button', { type: 'button', onClick: onClose }, 'Close'),
  );
}

/* Resource glyphs: eight original marks, one per server wallet slot. */
const ICON_COLORS: Record<string, { fill: string; stroke: string }> = {
  e: { fill: '#d9a441', stroke: '#77571a' },
  x: { fill: '#6e7fc1', stroke: '#36406b' },
  g: { fill: '#e0b13e', stroke: '#7a5c14' },
  w: { fill: '#9a7047', stroke: '#54402a' },
  o: { fill: '#4f6f86', stroke: '#2b3f4f' },
  s: { fill: '#7d8a96', stroke: '#3d464e' },
  c: { fill: '#5d9b6f', stroke: '#2d5a3a' },
  m: { fill: '#9a6eae', stroke: '#50355e' },
};

/** One original inline SVG mark, keyed only by the server's wallet key. */
function ResourceGlyph({ kind }: { readonly kind: string }): React.JSX.Element {
  const color = ICON_COLORS[kind] ?? { fill: '#8795a1', stroke: '#414d56' };
  const shape = (() => {
    switch (kind) {
      case 'e':
        return e('path', { d: 'M20 4 L10 19 h8 l-3 11 l13 -16 h-8 l4 -10 Z', fill: color.fill });
      case 'x':
        return e('path', {
          d: 'M20 5 l4 10 l10 1 l-8 6 l3 10 l-9 -6 l-9 6 l3 -10 l-8 -6 l10 -1 Z',
          fill: color.fill,
        });
      case 'g':
        return e('g', { fill: color.fill, stroke: color.stroke, strokeWidth: 1 },
          e('ellipse', { cx: 20, cy: 11, rx: 11, ry: 4 }),
          e('path', { d: 'M9 11 v5 c0 2 5 4 11 4 s11 -2 11 -4 v-5' }),
          e('path', { d: 'M9 18 v4 c0 2 5 4 11 4 s11 -2 11 -4 v-4' }),
        );
      case 'w':
        return e('g', { fill: color.fill, stroke: color.stroke, strokeWidth: 1 },
          e('rect', { x: 6, y: 9, width: 28, height: 7, rx: 2 }),
          e('rect', { x: 9, y: 18, width: 22, height: 7, rx: 2 }),
        );
      case 'o':
        return e('path', {
          d: 'M20 4 C20 4 9 16 9 22 a11 11 0 0 0 22 0 C31 16 20 4 20 4 Z',
          fill: color.fill,
        });
      case 's':
        return e('path', {
          d: 'M9 24 L14 12 h12 l5 12 Z',
          fill: color.fill,
          stroke: color.stroke,
          strokeWidth: 1,
        });
      case 'c':
        return e('g', { fill: color.fill, stroke: color.stroke, strokeWidth: 1 },
          e('rect', { x: 5, y: 11, width: 30, height: 18, rx: 2 }),
          e('circle', { cx: 20, cy: 20, r: 5, fill: color.stroke }),
        );
      default:
        return e('path', {
          d: 'M20 4 l3 12 l12 4 l-12 4 l-3 12 l-3 -12 l-12 -4 l12 -4 Z',
          fill: color.fill,
        });
    }
  })();
  return e(
    'svg',
    {
      className: 'swl-portrait-icon-glyph',
      viewBox: '0 0 40 40',
      role: 'img',
      'aria-hidden': 'true',
      'data-swl-resource-glyph': kind,
    },
    e('title', null, kind),
    shape,
  );
}

/**
 * The icon-panel layout primitive: a fixed grid of one icon per server wallet
 * slot. The number of columns is UI-only layout; the keys, labels and amounts
 * are the server's. With no finite amounts it draws an explicit empty state.
 */
export function IconPanel({ view }: { readonly view: IconPanelView }): React.JSX.Element {
  if (view.icons.length === 0) {
    return e(
      'div',
      { className: 'swl-portrait-icons-empty', 'data-swl-icon-panel': 'empty' },
      NO_ICONS_CAPTION,
    );
  }
  return e(
    'div',
    {
      className: 'swl-portrait-icons',
      'data-swl-icon-panel': 'icons',
      style: { gridTemplateColumns: `repeat(${view.columns}, minmax(0, 1fr))` },
    },
    ...view.icons.map((icon) =>
      e(
        'div',
        {
          key: icon.key,
          className: 'swl-portrait-icon',
          'data-swl-resource': icon.key,
          'data-swl-resource-amount': icon.amount,
          title: `${icon.label}: ${icon.amount}`,
        },
        e(ResourceGlyph, { kind: icon.key }),
        e('span', { className: 'swl-portrait-icon-label' }, icon.label),
        e('span', { className: 'swl-portrait-icon-amount' }, String(icon.amount)),
      ),
    ),
  );
}

/** The assault portraits: one original tile per unit the server accounts for. */
export function AssaultPortraits({
  view,
}: {
  readonly view: AssaultPortraitPanelView;
}): React.JSX.Element {
  if (view.portraits.length === 0) {
    return e(
      'div',
      { className: 'swl-assault-portraits-empty', 'data-swl-assault-portraits': 'empty' },
      NO_ASSAULT_PORTRAITS_CAPTION,
    );
  }
  return e(
    'ul',
    { className: 'swl-assault-portraits', 'data-swl-assault-portraits': 'roster' },
    ...view.portraits.map((unit) =>
      e(
        'li',
        {
          key: unit.itemId,
          className: `swl-assault-portrait${unit.allowed ? '' : ' swl-assault-portrait-excluded'}`,
          'data-swl-unit-id': unit.itemId,
          'data-swl-portrait-count': unit.available,
          'data-swl-settled': unit.settled ? 'true' : 'false',
        },
        e(PortraitFigure, {
          itemId: unit.itemId,
          state: !unit.settled ? 'unsettled' : unit.won ? 'won' : 'lost',
        }),
        e('span', { className: 'swl-assault-portrait-name' }, unit.name),
        e('span', { className: 'swl-assault-portrait-count' }, `×${unit.available}`),
      ),
    ),
  );
}
