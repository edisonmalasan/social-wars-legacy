/**
 * The collections tab of the storage panel.
 *
 * The catalogue is the **content's** ten collection rows; the held quantities
 * and the completed ids are the **server's** (`maps[0].store` and
 * `privateState.collections`), gathered by the pure model in `state.ts`. Every
 * row is a reading: the prize is only text from the content, and there is no
 * claim button here — awarding a prize is the server's job, never the
 * client's. The tab lives inside the storage panel, so it opens no second
 * modal and holds no game state.
 */
import type { CollectionsPanelView } from './state.ts';

/** The collections tab's props. */
export interface CollectionsProps {
  /** The content catalogue and the server's progress, read by `state.ts`. */
  readonly view: CollectionsPanelView;
}

/** The content's collections with the server's progress, as a read-only list. */
export function Collections({ view }: CollectionsProps): React.JSX.Element {
  return (
    <div className="swl-collections" aria-label="Collections" data-swl-collections="">
      {view.entries.length === 0 ? (
        <p className="swl-collections-empty">No collections in the content.</p>
      ) : (
        <ul className="swl-collections-list">
          {view.entries.map((entry) => (
            <li className="swl-collection" key={entry.id} data-swl-collection-id={entry.id}>
              <div className="swl-collection-head">
                <span className="swl-collection-name">{entry.name}</span>
                <span className="swl-collection-progress">
                  {entry.held}/{entry.items.length}
                </span>
                {entry.completed ? (
                  <span className="swl-collection-done">Complete</span>
                ) : null}
              </div>
              <p className="swl-collection-description">{entry.description}</p>
              <ul className="swl-collection-items">
                {entry.items.map((item) => (
                  <li
                    className={item.quantity > 0 ? 'swl-collection-item' : 'swl-collection-item is-missing'}
                    key={item.itemId}
                  >
                    <span className="swl-collection-item-name">{item.name}</span>
                    <span className="swl-collection-item-qty">×{item.quantity}</span>
                  </li>
                ))}
              </ul>
              <p className="swl-collection-prize">Prize: {entry.prize || 'not specified'}</p>
              {entry.cashPrice !== null ? (
                <p className="swl-collection-price">{entry.cashPrice} cash</p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
