/**
 * The store panel.
 *
 * The packs, their prices and the buy requests are the model's
 * (`packages/client/src/store.ts`), bridged by `apps/client/src/ui/state.ts`
 * from the content and the server's cash. This file is the disclosure shell;
 * the item buttons and all their art are drawn by `storeitems.tsx`. A click
 * sends a request through the one command transport; the server owns the
 * price, the roll and the reward, and its answer is drawn as feedback.
 */
import type { NativeCommand } from '@swl/client';

import type { StoreItemsPanelView } from './state.ts';
import { StoreItems } from './storeitems.tsx';

/** The store panel's props. */
export interface StoreProps {
  /** The store front, read from the content and the server's wallet. */
  readonly view: StoreItemsPanelView;
  /** Send the purchase through the client's one command transport. */
  readonly onCommand?: (command: NativeCommand) => void;
}

/**
 * The store, collapsed until the player opens it.
 *
 * The original's store is a movieclip behind a button; the clone's is a
 * labelled disclosure so it stays out of the way of play. Unaffordable tiers
 * are shown but disabled, so the player can see what the next pack costs.
 * An empty bundle or wallet is drawn as an explicit empty state rather than
 * hiding the panel, so the store never claims packs it cannot read.
 */
export function Store({ view, onCommand }: StoreProps): React.JSX.Element {
  return (
    <details className="swl-store">
      <summary className="swl-store-summary">Store · {view.packs.length} packs</summary>
      <StoreItems view={view} onCommand={onCommand} />
    </details>
  );
}
