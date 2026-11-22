/**
 * Original item-button chrome for the store front.
 *
 * Every shape below is drawn from scratch in inline SVG: a framed star
 * medallion, an empty shelf, a slotted coin and a small tier tile. Nothing is
 * copied, traced or extracted from the original client, its art files or any
 * proprietary artwork; there are no image files and no new dependencies. The
 * marks are decorative (`aria-hidden`) and the panel's text carries the
 * meaning.
 *
 * The pack's name, price and declared amounts are the content's, and the cash
 * that decides affordability is the server's. The only gesture is the
 * catalogue's `buy_offer_pack` command handed to the host's one command
 * transport. No price, roll, grant or limit is computed here.
 */
import type { NativeCommand } from '@swl/client';

import type { StoreItemPackView, StoreItemsPanelView } from './state.ts';

/** The item button's badge: an original framed star medallion. */
export function StoreItemBadge({ className }: { className?: string }): React.JSX.Element {
  return (
    <svg
      className={className}
      viewBox="0 0 48 48"
      width="48"
      height="48"
      aria-hidden="true"
      focusable="false"
    >
      <rect x="3" y="3" width="42" height="42" rx="8" fill="#1d2430" stroke="#f5c542" strokeWidth="3" />
      <rect x="8" y="8" width="32" height="32" rx="5" fill="none" stroke="#38445a" strokeWidth="1.5" />
      <path
        d="M24 12l3.6 7.4 8.1 1.2-5.9 5.7 1.4 8.1L24 30.4l-7.2 3.9 1.4-8-5.9-5.8 8.1-1.2z"
        fill="#f5c542"
        stroke="#e8e3d8"
        strokeWidth="1"
        strokeLinejoin="round"
      />
      <path d="M15 37h18" stroke="#8d97a8" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

/** An empty shelf: the explicit empty-state mark for an empty store. */
export function StoreItemEmptyArt({ className }: { className?: string }): React.JSX.Element {
  return (
    <svg
      className={className}
      viewBox="0 0 64 48"
      width="64"
      height="48"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M6 14h52M6 34h52" stroke="#8d97a8" strokeWidth="3" strokeLinecap="round" />
      <path d="M12 14v20M52 14v20" stroke="#38445a" strokeWidth="3" strokeLinecap="round" />
      <rect x="26" y="22" width="12" height="12" rx="2" fill="#1d2430" stroke="#f5c542" strokeWidth="2" strokeDasharray="3 3" />
      <path d="M30 9h4" stroke="#f5c542" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

/** A slotted coin: the original cash mark shown on a buy control. */
export function StoreItemCashMark({ className }: { className?: string }): React.JSX.Element {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width="24"
      height="24"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="12" cy="12" r="10" fill="#f5c542" stroke="#e8e3d8" strokeWidth="1.5" />
      <circle cx="12" cy="12" r="6.5" fill="none" stroke="#a9793e" strokeWidth="1" />
      <path d="M12 6v12M8 9.5h8M8 14.5h8" stroke="#6f4a22" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

/** One offer pack drawn as an original item button. */
export function StoreItemButton({
  pack,
  view,
  onCommand,
}: {
  readonly pack: StoreItemPackView;
  readonly view: StoreItemsPanelView;
  readonly onCommand?: (command: NativeCommand) => void;
}): React.JSX.Element {
  const superPack = pack.shape === 'super';
  return (
    <li className="swl-store-item" data-swl-pack={pack.id} data-swl-shape={pack.shape}>
      <StoreItemBadge className="swl-store-art-badge" />
      <div className="swl-store-item-main">
        <p className="swl-store-item-name">
          {pack.name}
          {superPack ? <span className="swl-store-item-flag">{view.limitedOffer}</span> : null}
        </p>
        {pack.contents.length > 0 ? (
          <p className="swl-store-item-contents">
            {view.earnings}{' '}
            {pack.contents.map((row) => `${row.key} ${row.amount}`).join(' · ')}{' '}
            <span className="swl-store-item-content-note">content values</span>
          </p>
        ) : null}
        {superPack ? (
          <div className="swl-store-item-tiers" role="group" aria-label={`${pack.name} tiers`}>
            {pack.tiers.map((tier) => (
              <button
                key={tier.count}
                type="button"
                className="swl-store-buy swl-store-item-buy"
                data-swl-pack={pack.id}
                data-swl-count={tier.count}
                disabled={!tier.affordable}
                onClick={() => onCommand?.(tier.command)}
              >
                <StoreItemCashMark className="swl-store-art-cash" />
                <span>{tier.count} · {tier.price}</span>
              </button>
            ))}
          </div>
        ) : pack.command ? (
          <button
            type="button"
            className="swl-store-buy swl-store-item-buy"
            data-swl-pack={pack.id}
            disabled={!pack.affordable}
            onClick={() => onCommand?.(pack.command!)}
          >
            <StoreItemCashMark className="swl-store-art-cash" />
            <span>{view.buyFor} {pack.price}</span>
          </button>
        ) : null}
      </div>
    </li>
  );
}

/** The store front's list of item buttons, with explicit empty states. */
export function StoreItems({
  view,
  onCommand,
}: {
  readonly view: StoreItemsPanelView;
  readonly onCommand?: (command: NativeCommand) => void;
}): React.JSX.Element {
  return (
    <div className="swl-store-items">
      <p className="swl-store-cash">
        Cash (server): <span data-swl-server="cash">{view.cash ?? 'not published'}</span>
      </p>
      {view.emptyMessages.length > 0 ? (
        <div className="swl-store-empty" role="status">
          <StoreItemEmptyArt className="swl-store-art-empty" />
          <ul className="swl-store-empty-list">
            {view.emptyMessages.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <ul className="swl-store-item-list">
        {view.packs.map((pack) => (
          <StoreItemButton key={pack.id} pack={pack} view={view} onCommand={onCommand} />
        ))}
      </ul>
    </div>
  );
}
