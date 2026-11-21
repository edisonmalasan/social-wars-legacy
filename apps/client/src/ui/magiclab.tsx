/**
 * The Research LAB panel.
 *
 * The page, the order of the spells, the learned/available/blocked labels and
 * what can be bought are the client model's (`magic.ts`, bridged in
 * `state.ts`). This file only draws them. Buying a spell or mana sends a
 * request; the server prices it, grants it and owns the mana counter.
 */
import { useState } from 'react';

import {
  buyMagic,
  buyMana,
  type NativeCommand,
  type WorldSnapshot,
} from '@swl/client';
import type { ContentBundle } from '@swl/content';

import { magicLabPanel } from './state.ts';

/** The Research LAB's props. */
export interface MagicLabProps {
  readonly bundle: ContentBundle;
  readonly world: WorldSnapshot;
  readonly onCommand?: (command: NativeCommand) => void;
}

/** A small row of filled spell-level stars, for display only. */
function Stars({ level }: { level: number }): React.JSX.Element {
  return (
    <span className="swl-magic-stars" aria-label={`Spell level ${level}`}>
      {'★'.repeat(level)}
      {'☆'.repeat(Math.max(0, 3 - level))}
    </span>
  );
}

/**
 * The Research LAB, collapsed until the player opens it.
 *
 * The client's quirk is kept: a spell below the unlock level hides its gold
 * button but leaves the cash button live, because cash bypasses the level
 * while gold does not.
 */
export function MagicLab({ bundle, world, onCommand }: MagicLabProps): React.JSX.Element {
  const [page, setPage] = useState(0);
  const view = magicLabPanel(bundle, world, page);
  const gold = Number(world.resources['g'] ?? 0);
  const cash = Number(world.resources['c'] ?? 0);

  return (
    <details className="swl-magiclab">
      <summary className="swl-magiclab-summary">
        Research LAB · {view.mana} mana
      </summary>
      <div className="swl-magiclab-body">
        <ul className="swl-magic-entries">
          {view.items.map((entry) => (
            <li className="swl-magic-entry" key={entry.id} data-swl-spell={entry.id}>
              <div className="swl-magic-entry-head">
                <span className="swl-magic-name">{entry.name}</span>
                <Stars level={entry.level} />
                <span className="swl-magic-status">{entry.status}</span>
              </div>
              <p className="swl-magic-description">{entry.description}</p>
              {entry.known ? (
                <span className="swl-magic-uses">
                  {entry.uses ?? 0} uses · area {entry.areaForLevel ?? '—'}
                </span>
              ) : (
                <span className="swl-magic-costs">
                  {entry.available && entry.gold > 0 ? (
                    <button
                      type="button"
                      className="swl-magic-buy"
                      disabled={gold < entry.gold}
                      onClick={() => onCommand?.(buyMagic(entry.id, 'g'))}
                    >
                      {entry.gold} gold
                    </button>
                  ) : null}
                  {entry.cash > 0 ? (
                    <button
                      type="button"
                      className="swl-magic-buy"
                      disabled={cash < entry.cash}
                      title={entry.available ? undefined : 'Unlock early with cash'}
                      onClick={() => onCommand?.(buyMagic(entry.id, 'c'))}
                    >
                      {entry.cash} cash
                    </button>
                  ) : null}
                  {!entry.available ? (
                    <span className="swl-magic-unlock">Level {entry.unlockLevel}</span>
                  ) : null}
                </span>
              )}
            </li>
          ))}
        </ul>
        <div className="swl-magic-packs" role="group" aria-label="Buy mana">
          {(['c', 'g'] as const).map((payment) => (
            <button
              key={payment}
              type="button"
              className="swl-magic-buy"
              disabled={!view.canBuyMana[payment]}
              onClick={() => onCommand?.(buyMana(view.pack.amount, payment))}
            >
              +{view.pack.amount} mana · {view.pack.price[payment]} {payment === 'c' ? 'cash' : 'gold'}
            </button>
          ))}
        </div>
        <div className="swl-magic-pages" role="group" aria-label="Spell pages">
          <button
            type="button"
            disabled={!view.canPrev}
            onClick={() => setPage((current) => Math.max(0, current - 1))}
          >
            Previous
          </button>
          <span>{view.page + 1} / {view.pageCount}</span>
          <button
            type="button"
            disabled={!view.canNext}
            onClick={() => setPage((current) => current + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </details>
  );
}
