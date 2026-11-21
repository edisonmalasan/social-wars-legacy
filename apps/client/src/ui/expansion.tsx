/**
 * The expansion control.
 *
 * The panel is a **reading** of two authoritative sources: the owned count is
 * the server's (its save's expansion list) and the price is the content's row
 * at that ordinal. A click sends the `expand(tileId)` request through the
 * client's one command transport; the server decides whether the tile may be
 * bought, and its answer is drawn in the shared feedback region. Nothing here
 * adds a tile or spends a resource on its own.
 */
import type { NativeCommand } from '@swl/client';

import type { ExpansionPanelView } from './state.ts';

/** The expansion control's props. */
export interface ExpansionProps {
  /** The server-derived view, or null when the content has no price to offer. */
  readonly view: ExpansionPanelView | null;
  /** Send the purchase through the client's command transport. */
  readonly onCommand?: (command: NativeCommand) => void;
}

/**
 * The expansion control, or nothing when there is no price to show.
 *
 * An inline panel like the goals panel: it reuses the interface's one feedback
 * channel for the server's answer and needs no second modal or piece of art.
 */
export function Expansion({ view, onCommand }: ExpansionProps): React.JSX.Element | null {
  if (!view) return null;
  return (
    <div className="swl-expansion">
      <div className="swl-expansion-head">Expand the town</div>
      <button
        type="button"
        className="swl-expansion-buy"
        onClick={() => onCommand?.(view.command)}
      >
        <span className="swl-expansion-label">Expand</span>
        <span className="swl-expansion-price">
          <span className="swl-expansion-gold">{view.coins} gold</span>
          <span className="swl-expansion-cash">{view.cash} cash</span>
        </span>
      </button>
    </div>
  );
}
