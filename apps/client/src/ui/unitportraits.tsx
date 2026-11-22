/**
 * Unit / training-queue portraits — original inline SVG geometry.
 *
 * This is the rendered counterpart of the three GUI classes `Portrait`,
 * `PortraitTrainQueue` and `AnimatedUnit`. It draws the state the server has
 * already published: the queue's `nu`/`ts`/`ui` (via `TrainingView`), the units
 * the server owns (army/stored items), and the names content supplies.
 *
 * Nothing here rolls a unit, grants a count, decides "ready", charges
 * anything, or sends a command. The host panels keep their existing train
 * and take gestures; this module only draws what those gestures produce.
 * Every shape and colour below is original geometry authored in this file —
 * there is no external image or raster reference of any kind.
 */
import * as React from 'react';

import type { TrainingView } from '@swl/client';

/** The animation state a portrait may show; all three are server/content reads. */
export type PortraitAnimation = 'owned' | 'training' | 'ready';

/** A portrait the client is allowed to draw. Every field comes from a source. */
export interface UnitPortraitView {
  /** The item id the server published. */
  readonly itemId: number;
  /** The content's name, or null when content does not name this id. */
  readonly name: string | null;
  /** The count the server published, never a client guess. */
  readonly count: number;
  /** Presentational state derived only from the server's queue / owned units. */
  readonly animation: PortraitAnimation;
}

/** Caption for a still-charging queue slot; never shown without a queue. */
export const TRAINING_CAPTION = 'Not charged yet';

/** Caption for a queue slot the server says can be taken. */
export const READY_CAPTION = 'Unit ready';

/** Caption for an empty queue — no portrait, no unit, no charge. */
export const EMPTY_CAPTION = 'No unit in training';

/** A finite, positive integer or null — the only ids/counts we will draw. */
function positive(value: unknown): number | null {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) return null;
  return Math.trunc(number);
}

/** The name content gives an id, or null rather than an invented one. */
function nameFor(
  itemId: number,
  units: readonly { readonly itemId: number; readonly name: string }[],
): string | null {
  for (const unit of units) {
    if (Number(unit.itemId) === itemId) return unit.name;
  }
  return null;
}

/**
 * Read the one portrait the server's training queue allows, or null for an
 * empty/malformed queue. A queue is only drawn when it names a real unit id
 * and holds a real count; `ready` is taken verbatim from the server's flag.
 */
export function queuePortrait(
  queue: TrainingView | null | undefined,
  units: readonly { readonly itemId: number; readonly name: string }[] = [],
): UnitPortraitView | null {
  if (!queue) return null;
  const itemId = positive(queue.unitItemId);
  const count = positive(queue.queued);
  if (itemId === null || count === null) return null;
  return {
    itemId,
    name: nameFor(itemId, units),
    count,
    animation: queue.readyToTake === true ? 'ready' : 'training',
  };
}

/**
 * The portraits for the units the server actually owns. A malformed id/count
 * is skipped rather than replaced with a fabricated unit.
 */
export function ownedPortraits(
  units: readonly {
    readonly itemId: number;
    readonly name: string;
    readonly count: number;
  }[],
): UnitPortraitView[] {
  const portraits: UnitPortraitView[] = [];
  for (const unit of units) {
    const itemId = positive(unit.itemId);
    const count = Number(unit.count);
    if (itemId === null || !Number.isFinite(count) || count < 0) continue;
    portraits.push({
      itemId,
      name: unit.name,
      count: Math.trunc(count),
      animation: 'owned',
    });
  }
  return portraits;
}

/** One owned unit's portrait, or null when the server row is malformed. */
export function ownedPortrait(
  unit: { readonly itemId: number; readonly name: string; readonly count: number } | null | undefined,
): UnitPortraitView | null {
  return unit ? ownedPortraits([unit])[0] ?? null : null;
}

/** The label shown for a portrait; a missing content name becomes the id. */
export function portraitLabel(view: UnitPortraitView): string {
  return view.name ?? `Unit ${view.itemId}`;
}

/** The state caption, only ever one the server's queue justifies. */
export function portraitCaption(view: UnitPortraitView): string | null {
  if (view.animation === 'ready') return READY_CAPTION;
  if (view.animation === 'training') return TRAINING_CAPTION;
  return null;
}

/* Original geometry only. The palette is indexed deterministically by the
 * server's id; there is no random roll and no asset lookup. */
const PALETTE = [
  { frame: '#34536e', field: '#edf3f8', body: '#4f7fa8', trim: '#d9a441' },
  { frame: '#54416e', field: '#f4eef9', body: '#7a5fa0', trim: '#d9a441' },
  { frame: '#355a4d', field: '#eaf5ee', body: '#4f9378', trim: '#d9a441' },
  { frame: '#6b4038', field: '#f8eee9', body: '#a86750', trim: '#d9a441' },
] as const;

function paletteFor(itemId: number) {
  const index = ((itemId % PALETTE.length) + PALETTE.length) % PALETTE.length;
  return PALETTE[index] ?? PALETTE[0]!;
}

/** Build a React element without JSX, so the file is loadable by Node's TS stripper. */
const e = React.createElement;

/**
 * One portrait: an original framed figure plus the server's id/count and the
 * queue's animation state. The SVG uses only shapes and text authored here.
 */
export function UnitPortrait({
  view,
  className,
}: {
  readonly view: UnitPortraitView;
  readonly className?: string;
}): React.JSX.Element {
  const palette = paletteFor(view.itemId);
  const caption = portraitCaption(view);
  return e(
    'svg',
    {
      className,
      viewBox: '0 0 96 120',
      role: 'img',
      'aria-label': `${portraitLabel(view)}, ${view.animation}`,
      'data-swl-portrait': '',
      'data-swl-unit-id': view.itemId,
      'data-swl-portrait-count': view.count,
      'data-swl-animation': view.animation,
    },
    e('title', null, portraitLabel(view)),
    // Frame and field — original geometry, no image or fill reference.
    e('rect', {
      x: 2,
      y: 2,
      width: 92,
      height: 92,
      rx: 8,
      fill: palette.frame,
      stroke: palette.trim,
      strokeWidth: 2,
    }),
    e('rect', { x: 8, y: 8, width: 80, height: 74, rx: 4, fill: palette.field }),
    // Shoulders and head — a stylised original figure, not a copied sprite.
    e('path', {
      d: 'M20 82 C20 56 34 48 48 48 C62 48 76 56 76 82 Z',
      fill: palette.body,
    }),
    e('circle', {
      cx: 48,
      cy: 34,
      r: 14,
      fill: palette.body,
      stroke: palette.frame,
      strokeWidth: 2,
    }),
    e('path', { d: 'M40 33 h5 M51 33 h5', stroke: palette.field, strokeWidth: 2, fill: 'none' }),
    e('path', { d: 'M43 41 Q48 45 53 41', stroke: palette.field, strokeWidth: 1.5, fill: 'none' }),
    // Queue animation states: a dashed charge ring, or the ready check. Both
    // exist only because the server's queue put the portrait in that state.
    view.animation === 'training'
      ? e('circle', {
          cx: 48,
          cy: 45,
          r: 30,
          fill: 'none',
          stroke: palette.trim,
          strokeWidth: 3,
          strokeDasharray: '6 6',
          'data-swl-animation-mark': 'charging',
        })
      : null,
    view.animation === 'ready'
      ? e('path', {
          d: 'M36 63 l8 8 l16 -18',
          fill: 'none',
          stroke: '#2f7a4f',
          strokeWidth: 5,
          strokeLinecap: 'round',
          'data-swl-animation-mark': 'ready',
        })
      : null,
    caption
      ? e(
          'text',
          {
            x: 48,
            y: 78,
            textAnchor: 'middle',
            fontSize: 9,
            fill: palette.frame,
            'data-swl-portrait-caption': '',
          },
          caption,
        )
      : null,
    // The count is the server's number, printed verbatim with a × prefix.
    e(
      'text',
      {
        x: 48,
        y: 110,
        textAnchor: 'middle',
        fontSize: 14,
        fill: palette.frame,
        'data-swl-portrait-count-text': '',
      },
      `×${view.count}`,
    ),
  );
}

/** The training-queue portraits for a recruit panel. */
export function TrainingQueuePortraits({
  queue,
  units = [],
}: {
  readonly queue: TrainingView | null | undefined;
  readonly units?: readonly { readonly itemId: number; readonly name: string }[];
}): React.JSX.Element {
  const portrait = queuePortrait(queue, units);
  if (!portrait) {
    return e(
      'div',
      { className: 'swl-portrait-queue-empty', 'data-swl-portraits': 'queue-empty' },
      EMPTY_CAPTION,
    );
  }
  return e(
    'div',
    { className: 'swl-portrait-queue', 'data-swl-portraits': 'queue' },
    e(UnitPortrait, { view: portrait }),
  );
}

/** The owned-unit portraits for a roster panel. */
export function OwnedUnitPortraits({
  units,
}: {
  readonly units: readonly {
    readonly itemId: number;
    readonly name: string;
    readonly count: number;
  }[];
}): React.JSX.Element {
  const portraits = ownedPortraits(units);
  return e(
    'div',
    { className: 'swl-portraits-owned', 'data-swl-portraits': 'owned' },
    ...portraits.map((view) => e(UnitPortrait, { key: view.itemId, view })),
  );
}
