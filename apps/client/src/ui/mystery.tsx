/**
 * The two mystery-box popups, hosted by the client's one shared dialog.
 *
 * `PopupMistery` shows what pack 4 could grant; `PopupSuperMistery` shows a
 * super pack's three rarity rows and three priced tiers. The preview is a
 * reading of the content's own pack and the popups' own literals, and both
 * Buy buttons only send a request — the server prices, rolls and grants.
 * Once it answers, the same dialog slot draws the items its store actually
 * gained instead of a client-side guess. No second modal and no proprietary
 * box artwork are involved.
 *
 * The host owns only UI state (which box is open, which answer is showing);
 * the game state stays the server's.
 */
import { useMemo, useSyncExternalStore } from 'react';

import type { ContentBundle } from '@swl/content';

import {
  mysteryBoxes,
  type MysteryBoxView,
  type MysteryLauncherView,
  type MysteryPurchase,
  type MysteryResultView,
} from './state.ts';

/** The host's UI-only mystery-box slot. */
export interface MysteryHost {
  /** The preview the open popup draws, or null when none is open. */
  readonly view: MysteryBoxView | null;
  /** The reward the server's last answer granted, or null before a buy. */
  readonly result: MysteryResultView | null;
  /** Open one of the two popups in the one shared dialog. */
  readonly open?: (launch: MysteryLauncherView) => void;
  /** Ask the server to buy a tier; the server owns the roll and the grant. */
  readonly buy?: (purchase: MysteryPurchase) => void;
}

const CLOSED_HOST: MysteryHost = { view: null, result: null };
let host: MysteryHost = CLOSED_HOST;
const listeners = new Set<() => void>();

/** Publish the UI-only body and gestures the host chose. */
export function setMysteryHost(patch: Partial<MysteryHost>): void {
  host = { ...host, ...patch };
  for (const listener of listeners) listener();
}

/** The current UI-only mystery-box slot. */
export function mysteryHost(): MysteryHost {
  return host;
}

/** Subscribe to changes in the mystery-box slot. */
export function subscribeMystery(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Read the mystery-box slot from a React component. */
export function useMystery(): MysteryHost {
  return useSyncExternalStore(subscribeMystery, mysteryHost, mysteryHost);
}

/** The two box buttons, built from the content's own pack ids and names. */
export function MysteryLauncher({ bundle }: { bundle: ContentBundle }): React.JSX.Element | null {
  const { open } = useMystery();
  const boxes = useMemo(() => mysteryBoxes(bundle), [bundle]);
  if (boxes.length === 0) return null;
  return (
    <details className="swl-mystery-launcher">
      <summary className="swl-mystery-launcher-summary">Mystery boxes</summary>
      <div className="swl-mystery-launcher-list">
        {boxes.map((box) => (
          <button
            key={`${box.kind}:${box.packId}`}
            type="button"
            className="swl-mystery-launch"
            data-swl-box={box.kind}
            data-swl-available={box.available}
            title={box.available ? box.name : `${box.name} (not currently offered)`}
            onClick={() => open?.(box)}
          >
            {box.title}
          </button>
        ))}
      </div>
    </details>
  );
}

/**
 * The body hosted by the one dialog: the preview before a buy, and the
 * server's answer after it. Only the OK/buy gestures live here; neither
 * changes the world, and neither opens another dialog.
 */
export function MysteryPanel({
  view,
  result,
  onClose,
}: {
  readonly view: MysteryBoxView | null;
  readonly result: MysteryResultView | null;
  readonly onClose?: () => void;
}): React.JSX.Element | null {
  const { buy } = useMystery();

  if (result) {
    return (
      <div className="swl-mystery-result" data-swl-mystery-result={result.kind} role="status">
        {result.heading ? <p className="swl-mystery-win">{result.heading}</p> : null}
        {result.message ? <p className="swl-mystery-storage">{result.message}</p> : null}
        <p className="swl-mystery-title">{result.title}</p>
        <ul className="swl-mystery-won">
          {result.items.map((item) => (
            <li key={item.itemId} data-swl-won={item.itemId}>
              {item.name}
              {item.quantity > 1 ? ` ×${item.quantity}` : ''}
            </li>
          ))}
        </ul>
        {result.price !== null ? (
          <p className="swl-mystery-price">{result.price} cash</p>
        ) : null}
        <button type="button" className="swl-mystery-ok" onClick={onClose}>
          {result.ok}
        </button>
      </div>
    );
  }

  if (!view) return null;
  return (
    <div className="swl-mystery" data-swl-mystery={view.packId}>
      <p className="swl-mystery-title">{view.title}</p>
      <p className="swl-mystery-prompt">{view.prompt}</p>
      {view.banner ? <p className="swl-mystery-banner">{view.banner}</p> : null}
      {view.weekNote ? <p className="swl-mystery-week">{view.weekNote}</p> : null}
      <div className="swl-mystery-rows">
        {view.rows.map((row, index) => (
          <div
            className="swl-mystery-row"
            data-swl-rarity={row.label}
            key={`${row.label}:${index}`}
          >
            <span className="swl-mystery-rarity">{row.label}</span>
            <span className="swl-mystery-candidates">
              {row.items.map((item) => (
                <span key={item.itemId} data-swl-candidate={item.itemId}>
                  {item.name}
                </span>
              ))}
            </span>
          </div>
        ))}
      </div>
      {view.tiers.map((tier) => (
        <button
          key={tier.count}
          type="button"
          className="swl-mystery-buy"
          data-swl-tier={tier.count}
          disabled={!tier.affordable}
          onClick={() =>
            buy?.({
              kind: view.kind,
              packId: view.packId,
              title: view.title,
              price: tier.price,
              command: tier.command,
            })
          }
        >
          {view.buy} · {tier.price} cash
        </button>
      ))}
      {view.tiers.length === 0 ? (
        <p className="swl-mystery-unavailable">Not currently offered</p>
      ) : null}
    </div>
  );
}
