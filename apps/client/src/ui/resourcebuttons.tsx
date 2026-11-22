/**
 * Resource buttons, resource icons and the resources tab — original inline
 * SVG geometry only.
 *
 * This is the rendered counterpart of `ButtonResourceMC.as`,
 * `ButtonSmallLargeTextWithIconResourcesMC.as`,
 * `ButtonSmallWithIconResourcesMC.as`, `IconResourcesMC.as` and
 * `GUI/ResourcesTab.as`. All five are presentation over a readout the HUD
 * already draws and gestures the command catalogue already prices. The
 * launcher and its one dialog panel draw that presentation; they add no rule.
 *
 * Every shape, path and colour below is authored here from scratch. There is
 * no copied, traced or extracted art, no image file, no raster reference and
 * no external URL of any kind. The marks are decorative (`aria-hidden`) and
 * the text beside them carries the meaning.
 *
 * The values are the server's verbatim, read through `resourceButtonsPanel`.
 * The only gesture is the catalogue's `trade_resource` command, handed to the
 * host's one command transport. Nothing here grants a resource, computes a
 * price, predicts a balance or starts a countdown.
 */
import * as React from 'react';

import type { NativeCommand } from '@swl/client';

import {
  RESOURCE_BUTTONS_NO_STATE,
  type ResourceButtonsPanelView,
  type ResourceShortcutView,
} from './state.ts';

/** The only UI state this family owns: whether its panel is showing. */
export interface ResourceButtonsHost {
  readonly open: boolean;
}

const CLOSED_HOST: ResourceButtonsHost = { open: false };
let host: ResourceButtonsHost = CLOSED_HOST;
const listeners = new Set<() => void>();

/** Publish the launcher's open/closed gesture. */
export function setResourceButtonsHost(patch: Partial<ResourceButtonsHost>): void {
  host = { ...host, ...patch };
  for (const listener of listeners) listener();
}

/** The current launcher state, for tests and for the view. */
export function resourceButtonsHost(): ResourceButtonsHost {
  return host;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Read the launcher's state from a component. */
export function useResourceButtons(): ResourceButtonsHost {
  return React.useSyncExternalStore(subscribe, resourceButtonsHost, resourceButtonsHost);
}

/** Close the panel from its own button or from the shared dialog. */
export function closeResourceButtonsPanel(): void {
  setResourceButtonsHost({ open: false });
}

/** Original palette per wire key; the fallback is the same authored geometry. */
const MARKS: Readonly<Record<string, { readonly face: string; readonly trim: string }>> = {
  e: { face: '#86d38a', trim: '#2f7a4f' }, // energy — a bolt
  x: { face: '#c3a2e8', trim: '#5b3f86' }, // xp — a rising bar
  g: { face: '#f5c542', trim: '#a9793e' }, // gold — a coin
  w: { face: '#a2c67a', trim: '#4c6b32' }, // wood — a stacked log
  o: { face: '#7fa8c9', trim: '#34546f' }, // oil — a drop
  s: { face: '#b9c3cc', trim: '#5c6678' }, // steel — a riveted bar
  c: { face: '#e0a95f', trim: '#8a5a22' }, // cash — a slotted token
  m: { face: '#8fb6e8', trim: '#3b5c9a' }, // mana — a crystal
};

function palette(key: string): { face: string; trim: string } {
  return MARKS[key] ?? { face: '#8d97a8', trim: '#38445a' };
}

/** Build a React element without JSX, so Node's TS stripper can load this file. */
const e = React.createElement;

/** The framed shortcut badge drawn on the launcher and the panel head. */
export function ResourceButtonBadge({ className }: { className?: string }): React.JSX.Element {
  return e(
    'svg',
    {
      className,
      viewBox: '0 0 48 48',
      width: '48',
      height: '48',
      'aria-hidden': 'true',
      focusable: 'false',
      'data-swl-art': 'resource-badge',
    },
    e('rect', {
      x: '2', y: '2', width: '44', height: '44', rx: '9',
      fill: '#1d2430', stroke: '#f5c542', strokeWidth: '3',
    }),
    e('rect', {
      x: '8', y: '8', width: '32', height: '32', rx: '5',
      fill: 'none', stroke: '#38445a', strokeWidth: '1.5',
    }),
    // An original stack of three resource bars, not a traced game sprite.
    e('rect', { x: '14', y: '15', width: '20', height: '4', rx: '2', fill: '#f5c542' }),
    e('rect', { x: '14', y: '22', width: '14', height: '4', rx: '2', fill: '#8d97a8' }),
    e('rect', { x: '14', y: '29', width: '9', height: '4', rx: '2', fill: '#8d97a8' }),
    e('path', {
      d: 'M33 30 l5 -6 M38 24 l-0.5 5 M38 24 l-5 0.5',
      fill: 'none', stroke: '#e8e3d8', strokeWidth: '2', strokeLinecap: 'round',
    }),
  );
}

/**
 * One resource's icon mark, drawn from authored geometry. The shape is chosen
 * by the wire key; no file, font glyph or URL is ever referenced.
 */
export function ResourceIconMark({
  mark,
  className,
}: {
  readonly mark: string;
  readonly className?: string;
}): React.JSX.Element {
  const ink = palette(mark);
  let body: React.ReactNode;
  switch (mark) {
    case 'e':
      body = e('path', {
        d: 'M13 3 L8 13 h5 l-2 8 l9 -12 h-5 l3 -6 z',
        fill: ink.face, stroke: ink.trim, strokeWidth: '1.2', strokeLinejoin: 'round',
      });
      break;
    case 'x':
      body = e('path', {
        d: 'M5 19 L9 13 l4 3 l6 -11 l2 2 l-8 14 l-4 -3 l-4 6 z',
        fill: ink.face, stroke: ink.trim, strokeWidth: '1.2', strokeLinejoin: 'round',
      });
      break;
    case 'g':
      body = e('path', {
        d: 'M12 2 l4.5 3 l3.5 7 l-3.5 7 L12 22 l-4.5 -3 L4 12 l3.5 -7 z',
        fill: ink.face, stroke: ink.trim, strokeWidth: '1.4', strokeLinejoin: 'round',
      });
      break;
    case 'w':
      body = e('path', {
        d: 'M4 7 h16 v4 H4 z M6 11 h12 v4 H6 z M8 15 h8 v4 H8 z',
        fill: ink.face, stroke: ink.trim, strokeWidth: '1.2', strokeLinejoin: 'round',
      });
      break;
    case 'o':
      body = e('path', {
        d: 'M12 2 C12 2 5 10 5 15 a7 7 0 0 0 14 0 C19 10 12 2 12 2 z',
        fill: ink.face, stroke: ink.trim, strokeWidth: '1.4', strokeLinejoin: 'round',
      });
      break;
    case 's':
      body = e('path', {
        d: 'M3 8 h18 v8 H3 z M6 11 h2 M16 11 h2 M6 14 h2 M16 14 h2',
        fill: ink.face, stroke: ink.trim, strokeWidth: '1.4', strokeLinejoin: 'round',
      });
      break;
    case 'c':
      body = e('path', {
        d: 'M12 2 l9 4 v6 c0 5 -4 8 -9 10 c-5 -2 -9 -5 -9 -10 V6 z M9 11 h6 M12 8 v7',
        fill: ink.face, stroke: ink.trim, strokeWidth: '1.4', strokeLinejoin: 'round',
      });
      break;
    default:
      body = e('path', {
        d: 'M12 2 L20 12 L12 22 L4 12 z M8 12 h8',
        fill: ink.face, stroke: ink.trim, strokeWidth: '1.4', strokeLinejoin: 'round',
      });
      break;
  }
  return e(
    'svg',
    {
      className,
      viewBox: '0 0 24 24',
      width: '24',
      height: '24',
      'aria-hidden': 'true',
      focusable: 'false',
      'data-swl-art': 'resource-icon',
      'data-swl-mark': mark,
    },
    body,
  );
}

/** The tab's authored slot geometry; it carries the client's own caption. */
export function ResourceTabMark({ className }: { className?: string }): React.JSX.Element {
  return e(
    'svg',
    {
      className,
      viewBox: '0 0 32 16',
      width: '32',
      height: '16',
      'aria-hidden': 'true',
      focusable: 'false',
      'data-swl-art': 'resource-tab',
    },
    e('path', {
      d: 'M2 15 L6 3 h20 l4 12 z',
      fill: '#223047', stroke: '#f5c542', strokeWidth: '1.5', strokeLinejoin: 'round',
    }),
    e('path', { d: 'M9 8 h14', stroke: '#8d97a8', strokeWidth: '1.5', strokeLinecap: 'round' }),
  );
}

/** The explicit empty-state mark: an empty tray, not a zero balance. */
export function ResourceButtonsEmptyArt({
  className,
}: {
  readonly className?: string;
}): React.JSX.Element {
  return e(
    'svg',
    {
      className,
      viewBox: '0 0 64 48',
      width: '64',
      height: '48',
      'aria-hidden': 'true',
      focusable: 'false',
      'data-swl-art': 'resource-empty',
    },
    e('path', { d: 'M6 13 h52 M6 35 h52', stroke: '#8d97a8', strokeWidth: '3', strokeLinecap: 'round' }),
    e('path', { d: 'M12 13 v22 M52 13 v22', stroke: '#38445a', strokeWidth: '3', strokeLinecap: 'round' }),
    e('rect', {
      x: '25', y: '20', width: '14', height: '12', rx: '2',
      fill: '#1d2430', stroke: '#f5c542', strokeWidth: '2', strokeDasharray: '3 3',
    }),
    e('path', { d: 'M29 8 h6', stroke: '#f5c542', strokeWidth: '2', strokeLinecap: 'round' }),
  );
}

/** The chrome's resource shortcut: open the one dialog, draw no game state. */
export function ResourceButtonsLauncher(): React.JSX.Element {
  const { open } = useResourceButtons();
  return e(
    'button',
    {
      type: 'button',
      className: 'swl-resource-buttons-launcher',
      'data-swl-open': String(open),
      'aria-label': 'Open the resource shortcuts',
      'aria-expanded': String(open),
      onClick: () => setResourceButtonsHost({ open: true }),
    },
    e(ResourceButtonBadge, { className: 'swl-resource-buttons-art-badge' }),
    e('span', null, 'Resources'),
  );
}

/** One small labelled resource button with its icon and the server's value. */
function ShortcutRow({
  shortcut,
  onTrade,
}: {
  readonly shortcut: ResourceShortcutView;
  readonly onTrade?: (command: NativeCommand) => void;
}): React.JSX.Element {
  return e(
    'li',
    {
      className: 'swl-resource-buttons-shortcut',
      'data-swl-resource': shortcut.key,
      'data-swl-server-key': shortcut.key,
    },
    e(ResourceIconMark, {
      mark: shortcut.key,
      className: 'swl-resource-buttons-art-icon',
    }),
    e(
      'div',
      { className: 'swl-resource-buttons-shortcut-main' },
      e('p', { className: 'swl-resource-buttons-label' }, shortcut.label),
      e(
        'p',
        { className: 'swl-resource-buttons-numbers' },
        'Server value: ',
        e('span', { 'data-swl-server': 'value' }, shortcut.value),
        shortcut.limit !== null
          ? e('span', { className: 'swl-resource-buttons-limit' }, ` · content limit ${shortcut.limit}`)
          : null,
      ),
      shortcut.trade.length > 0
        ? e(
            'div',
            {
              className: 'swl-resource-buttons-trades',
              role: 'group',
              'aria-label': `${shortcut.label} trades`,
            },
            ...shortcut.trade.map((command: NativeCommand) =>
              e(
                'button',
                {
                  key: `trade:${String(command.args[2])}`,
                  type: 'button',
                  className: 'swl-resource-buttons-trade',
                  'data-swl-command': command.name,
                  'data-swl-command-args': `${shortcut.key},0,${String(command.args[2])}`,
                  // The host owns the one transport; it decides whether the
                  // server accepts this catalogue request.
                  onClick: () => onTrade?.(command),
                },
                `Trade ${String(command.args[2])}`,
              ),
            ),
          )
        : null,
    ),
  );
}

/** The panel body the one dialog hosts. */
export function ResourceButtonsPanel({
  view,
  onCommand,
  onClose,
}: {
  readonly view: ResourceButtonsPanelView;
  /** The client's one command transport; no local grant or price is made. */
  readonly onCommand?: (command: NativeCommand) => void;
  readonly onClose?: () => void;
}): React.JSX.Element {
  return e(
    'div',
    {
      className: 'swl-resource-buttons',
      'data-swl-resource-buttons': 'chrome',
    },
    e(
      'div',
      { className: 'swl-resource-buttons-head' },
      e(ResourceButtonBadge, { className: 'swl-resource-buttons-art-badge' }),
      e(
        'div',
        null,
        e('p', { className: 'swl-resource-buttons-title' }, view.title),
        e('p', { className: 'swl-resource-buttons-note' }, view.note),
      ),
    ),
    e(
      'div',
      {
        className: 'swl-resource-buttons-tabs',
        role: 'tablist',
        'aria-label': 'Resource tabs',
      },
      e(
        'div',
        {
          className: 'swl-resource-buttons-tab',
          role: 'tab',
          'aria-selected': 'true',
          'data-swl-tab': 'resources',
        },
        e(ResourceTabMark, { className: 'swl-resource-buttons-art-tab' }),
        e('span', null, view.tab),
      ),
    ),
    view.shortcuts.length === 0
      ? e(
          'div',
          { className: 'swl-resource-buttons-empty', role: 'status', 'data-swl-empty': 'true' },
          e(ResourceButtonsEmptyArt, { className: 'swl-resource-buttons-art-empty' }),
          e(
            'ul',
            { className: 'swl-resource-buttons-empty-list' },
            ...(view.emptyMessages.length > 0
              ? view.emptyMessages.map((message) => e('li', { key: message }, message))
              : [e('li', { key: 'empty' }, RESOURCE_BUTTONS_NO_STATE)]),
          ),
        )
      : e(
          'ul',
          { className: 'swl-resource-buttons-list' },
          ...view.shortcuts.map((shortcut) =>
            e(ShortcutRow, { key: shortcut.key, shortcut, onTrade: onCommand }),
          ),
        ),
    e(
      'div',
      { className: 'swl-resource-buttons-footer' },
      e('button', { type: 'button', className: 'swl-resource-buttons-close', onClick: onClose }, 'Close'),
    ),
  );
}
