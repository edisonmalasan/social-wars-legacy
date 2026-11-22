/**
 * The player-owned resource market's launcher and panel.
 *
 * The two audited screens are `ButtonMarketMC.as` (only a movieclip) and
 * `popups/ButtonMarket.as` (a buy button, a sell button, a refresh and one
 * 24-hour exhaustion sentence). The launcher gesture lives in the chrome; the
 * panel is hosted by the client's one shared dialog in `root.tsx`.
 *
 * The panel is a reading, never an authority. Its counters and wallet come
 * from the server's answer through `marketPanel`; the content's price and
 * period numbers are shown as text only. Nothing here multiplies a price by
 * an amount, predicts a gold balance or disables a button because of the
 * exhaustion caption. Every buy or sell hands the command catalogue's
 * `trade_resource` to the host's one command transport; the server prices and
 * grants it. All art is the original inline geometry in `market-art.tsx`.
 */
import { useSyncExternalStore } from 'react';

import type { NativeCommand } from '@swl/client';

import {
  MARKET_LEGACY_LABELS,
  type MarketPanelView,
} from './state.ts';
import {
  MarketBadge,
  MarketEmptyArt,
  MarketExhaustedArt,
  MarketResourceMark,
} from './market-art.tsx';

/** The only UI state this family owns: whether its panel is showing. */
export interface MarketHost {
  readonly open: boolean;
}

const CLOSED_HOST: MarketHost = { open: false };
let host: MarketHost = CLOSED_HOST;
const listeners = new Set<() => void>();

/** Publish the launcher's open/closed gesture. */
export function setMarketHost(patch: Partial<MarketHost>): void {
  host = { ...host, ...patch };
  for (const listener of listeners) listener();
}

/** The current launcher state, for tests and for the view. */
export function marketHost(): MarketHost {
  return host;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Read the launcher's state from a component. */
export function useMarket(): MarketHost {
  return useSyncExternalStore(subscribe, marketHost, marketHost);
}

/** Close the panel from its own button or from the shared dialog. */
export function closeMarketPanel(): void {
  setMarketHost({ open: false });
}

/** The chrome's market gesture: open the panel in the one shared dialog. */
export function MarketLauncher(): React.JSX.Element {
  const { open } = useMarket();
  return (
    <button
      type="button"
      className="swl-market-launcher"
      data-swl-open={open}
      aria-label="Open the resource market"
      aria-expanded={open}
      onClick={() => setMarketHost({ open: true })}
    >
      <MarketBadge className="swl-market-art-badge" />
      <span>Market</span>
    </button>
  );
}

/** The panel body the one dialog hosts. */
export function MarketPanel({
  view,
  onCommand,
  onClose,
}: {
  readonly view: MarketPanelView;
  readonly onCommand?: (command: NativeCommand) => void;
  readonly onClose?: () => void;
}): React.JSX.Element {
  return (
    <div className="swl-market" data-swl-market="player-owned">
      <div className="swl-market-head">
        <MarketBadge className="swl-market-art-badge" />
        <div>
          <p className="swl-market-title">{view.title}</p>
          <p className="swl-market-note">
            The server prices every trade and grants the result.
          </p>
        </div>
      </div>

      {view.emptyMessages.length > 0 ? (
        <div className="swl-market-empty" role="status">
          <MarketEmptyArt className="swl-market-art-empty" />
          <ul className="swl-market-empty-list">
            {view.emptyMessages.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {view.counters ? (
        <dl className="swl-market-counters">
          <div>
            <dt>Trades this period (server)</dt>
            <dd data-swl-server="trades-done">{view.counters.tradesDone}</dd>
          </div>
          <div>
            <dt>Last trade (server timestamp)</dt>
            <dd data-swl-server="last-trade">{view.counters.lastTradeAt}</dd>
          </div>
          <div>
            <dt>First-time flag (server)</dt>
            <dd data-swl-server="first-time">{String(view.counters.firstTime)}</dd>
          </div>
          <div>
            <dt>Resources traded (server)</dt>
            <dd data-swl-server="resources-traded">
              {Object.entries(view.counters.resourcesTraded)
                .map(([key, amount]) => `${key}: ${amount}`)
                .join(', ') || 'none'}
            </dd>
          </div>
        </dl>
      ) : null}

      {view.wallet ? (
        <dl className="swl-market-wallet">
          <div>
            <dt>Gold (server)</dt>
            <dd data-swl-server="gold">{view.wallet.gold}</dd>
          </div>
          <div>
            <dt>Wood (server)</dt>
            <dd data-swl-server="wood">{view.wallet.wood}</dd>
          </div>
          <div>
            <dt>Oil (server)</dt>
            <dd data-swl-server="oil">{view.wallet.oil}</dd>
          </div>
          <div>
            <dt>Steel (server)</dt>
            <dd data-swl-server="steel">{view.wallet.steel}</dd>
          </div>
        </dl>
      ) : null}

      <p className="swl-market-display">
        {view.display.periodHours !== null
          ? `Content period: ${view.display.periodHours} hours. `
          : null}
        {view.display.maxTrades !== null
          ? `Content trade limit: ${view.display.maxTrades}. `
          : null}
        Content labels: {MARKET_LEGACY_LABELS.join(' · ')}.
      </p>

      <p
        className="swl-market-exhaustion"
        data-swl-display-only="true"
        role={view.exhausted ? 'status' : undefined}
      >
        <MarketExhaustedArt className="swl-market-art-exhausted" />
        <span>{view.exhaustion}</span>
      </p>

      <ul className="swl-market-rows">
        {view.resources.map((row) => (
          <li key={row.resource} className="swl-market-row" data-swl-resource={row.resource}>
            <MarketResourceMark resource={row.resource} className="swl-market-art-resource" />
            <div className="swl-market-row-main">
              <p className="swl-market-row-name">
                {row.label} <span className="swl-market-row-key">({row.resource})</span>
              </p>
              <p className="swl-market-row-numbers">
                {row.held !== null ? `held ${row.held} · ` : ''}
                {row.traded !== null ? `traded ${row.traded} · ` : ''}
                {row.baseCost !== null
                  ? `content base ${row.baseCost} gold per 100 (display only)`
                  : 'no content base published'}
              </p>
              <div className="swl-market-actions" role="group" aria-label={`${row.label} trades`}>
                {row.buy.map((command) => (
                  <button
                    key={`buy:${String(command.args[2])}`}
                    type="button"
                    className="swl-market-trade swl-market-buy"
                    data-swl-trade="buy"
                    data-swl-amount={String(command.args[2])}
                    onClick={() => onCommand?.(command)}
                  >
                    {view.buyLabel} {String(command.args[2])}
                  </button>
                ))}
                {row.sell.map((command) => (
                  <button
                    key={`sell:${String(command.args[2])}`}
                    type="button"
                    className="swl-market-trade swl-market-sell"
                    data-swl-trade="sell"
                    data-swl-amount={String(command.args[2])}
                    onClick={() => onCommand?.(command)}
                  >
                    {view.sellLabel} {String(command.args[2])}
                  </button>
                ))}
              </div>
            </div>
          </li>
        ))}
      </ul>

      <div className="swl-market-actions swl-market-footer">
        <button type="button" className="swl-market-close" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}
