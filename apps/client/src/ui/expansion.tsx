/**
 * The expansion control, its buy-for prompt and its growth result.
 *
 * The panel is a **reading** of two authoritative sources: the owned count is
 * the server's (its save's expansion list) and the price is the content's row
 * at that ordinal. A click sends the `expand(tileId)` request through the
 * client's one command transport; the server decides whether the tile may be
 * bought, and its answer is drawn in the shared feedback region. Nothing here
 * adds a tile or spends a resource on its own.
 *
 * The original's `ItemButtonLargeExpand2` prompt and its `PopupExpand`
 * celebration are drawn **inline**, in this one panel, from the content row
 * and from two of the server's answers. The requirement hints are the
 * original's own literals, never enforced gates, and the button stays the one
 * gesture. The Share! popup and the proprietary `expGen.png` art are excluded.
 */
import { useSyncExternalStore } from 'react';

import type { NativeCommand } from '@swl/client';

import {
  EXPANSION_RESULT_ID,
  type ExpansionPanelView,
  type ExpansionResultView,
} from './state.ts';

/** The host's UI-only result slot, set from the answer to an expand request. */
export interface ExpansionHost {
  /** The growth the server published, or null when no expansion was accepted. */
  readonly result: ExpansionResultView | null;
}

const CLOSED_HOST: ExpansionHost = { result: null };
let host: ExpansionHost = CLOSED_HOST;
const listeners = new Set<() => void>();

/** Publish the result the host read from the server's latest answer. */
export function setExpansionHost(patch: Partial<ExpansionHost>): void {
  host = { ...host, ...patch };
  for (const listener of listeners) listener();
}

/** The current UI-only expansion result slot. */
export function expansionHost(): ExpansionHost {
  return host;
}

/** Subscribe to changes in the expansion result slot. */
export function subscribeExpansion(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Read the expansion result from a React component. */
export function useExpansion(): ExpansionHost {
  return useSyncExternalStore(subscribeExpansion, expansionHost, expansionHost);
}

/** Dismiss the inline celebration; it changes no world state. */
export function clearExpansionResult(): void {
  setExpansionHost({ result: null });
}

/** The inline growth result: the server's new tiles and the content's price. */
function ExpansionResult({ view }: { view: ExpansionResultView }): React.JSX.Element {
  const price =
    view.coins !== null || view.cash !== null
      ? [
          view.coins !== null ? `${view.coins} gold` : null,
          view.cash !== null ? `${view.cash} cash` : null,
        ].filter((row) => row !== null).join(' · ')
      : null;
  return (
    <div
      className="swl-expansion-result"
      id={EXPANSION_RESULT_ID}
      data-swl-expansion-result=""
      role="status"
    >
      <p className="swl-expansion-result-head">{view.heading}</p>
      <p className="swl-expansion-result-message">{view.message}</p>
      <p className="swl-expansion-result-detail">
        {view.after} tiles · {view.tiles.length === 1 ? 'tile' : 'tiles'}{' '}
        {view.tiles.join(', ')}
      </p>
      {price ? <p className="swl-expansion-result-price">Price {price}</p> : null}
      <button
        type="button"
        className="swl-expansion-result-dismiss"
        onClick={clearExpansionResult}
      >
        OK
      </button>
    </div>
  );
}

/** The expansion control's props. */
export interface ExpansionProps {
  /** The server-derived view, or null when the content has no price to offer. */
  readonly view: ExpansionPanelView | null;
  /** Send the purchase through the client's command transport. */
  readonly onCommand?: (command: NativeCommand) => void;
}

/**
 * The expansion control, or nothing when there is neither a price nor a result.
 *
 * An inline panel like the goals panel: it reuses the interface's one feedback
 * channel for the server's answer and needs no second modal or piece of art.
 */
export function Expansion({ view, onCommand }: ExpansionProps): React.JSX.Element | null {
  const { result } = useExpansion();
  if (!view && !result) return null;
  return (
    <div className="swl-expansion">
      {result ? <ExpansionResult view={result} /> : null}
      {view ? (
        <>
          <div className="swl-expansion-head">Expand the town</div>
          <button
            type="button"
            className="swl-expansion-buy"
            onClick={() => onCommand?.(view.command)}
          >
            <span className="swl-expansion-label">Expand</span>
            <span className="swl-expansion-buyfor">{view.buyFor}</span>
            <span className="swl-expansion-price">
              <span className="swl-expansion-gold">{view.coins} gold</span>
              <span className="swl-expansion-cash">{view.cash} cash</span>
            </span>
          </button>
          {view.prompts.map((prompt) => (
            <p className="swl-expansion-prompt" data-swl-prompt={prompt.kind} key={prompt.kind}>
              {prompt.text}
            </p>
          ))}
        </>
      ) : null}
    </div>
  );
}
