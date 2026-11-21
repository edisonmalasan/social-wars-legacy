/**
 * The store panel.
 *
 * The packs, their prices and the buy requests are the model's
 * (`packages/client/src/store.ts`), which reads the content and the player's
 * cash. This file only draws them. A click sends a request; the server owns
 * the price, the roll and the reward, and its answer is drawn as feedback.
 */
import type { NativeCommand, StorePackView } from '@swl/client';

/** The store panel's props. */
export interface StoreProps {
  /** The packs the client may offer, from the content and the wallet. */
  readonly packs: readonly StorePackView[];
  /** Send the purchase through the client's one command transport. */
  readonly onCommand?: (command: NativeCommand) => void;
}

/**
 * The store, collapsed until the player opens it.
 *
 * The original's store is a movieclip behind a button; the clone's is a
 * labelled disclosure so it stays out of the way of play. Unaffordable tiers
 * are shown but disabled, so the player can see what the next pack costs.
 */
export function Store({ packs, onCommand }: StoreProps): React.JSX.Element | null {
  if (packs.length === 0) return null;
  return (
    <details className="swl-store">
      <summary className="swl-store-summary">Store · {packs.length} packs</summary>
      <div className="swl-store-packs">
        {packs.map((pack) => (
          <div className="swl-store-pack" key={pack.id} data-swl-pack={pack.id}>
            <div className="swl-store-pack-name">{pack.name}</div>
            {pack.shape === 'super' ? (
              <div className="swl-store-tiers">
                {pack.tiers.map((tier) => (
                  <button
                    key={tier.count}
                    type="button"
                    className="swl-store-buy"
                    disabled={!tier.affordable}
                    onClick={() => onCommand?.(tier.command)}
                  >
                    {tier.count} item{tier.count === 1 ? '' : 's'} · {tier.price} cash
                  </button>
                ))}
              </div>
            ) : pack.command ? (
              <button
                type="button"
                className="swl-store-buy"
                disabled={!pack.affordable}
                onClick={() => onCommand?.(pack.command!)}
              >
                {pack.price} cash
              </button>
            ) : null}
          </div>
        ))}
      </div>
    </details>
  );
}
