/**
 * The battle spell book.
 *
 * The learned spells, their levels, the page size and what the server-issued
 * mana can pay for are the client model's (`magic.ts`, bridged in `state.ts`).
 * This file only draws them. Casting is a `use_magic` request; the server
 * deducts the mana, counts the use and owns any battle effect.
 */
import { useState } from 'react';

import { useMagic, type NativeCommand, type WorldSnapshot } from '@swl/client';
import type { ContentBundle } from '@swl/content';

import { magicBookPanel } from './state.ts';

/** The spell book's props. */
export interface SpellBookProps {
  readonly bundle: ContentBundle;
  readonly world: WorldSnapshot;
  readonly onCommand?: (command: NativeCommand) => void;
}

/**
 * The spell book, collapsed until the player opens it.
 *
 * A spell with too little mana is shown but cannot be sent: the server would
 * refuse it. The mana price is the character's own, printed for reading.
 */
export function SpellBook({ bundle, world, onCommand }: SpellBookProps): React.JSX.Element {
  const [page, setPage] = useState(0);
  const view = magicBookPanel(bundle, world, page);

  return (
    <details className="swl-spellbook">
      <summary className="swl-spellbook-summary">
        Spell book · {view.mana} mana
      </summary>
      <div className="swl-spellbook-body">
        {view.items.length === 0 ? (
          <p className="swl-spellbook-empty">No spells learned yet.</p>
        ) : (
          <ul className="swl-spellbook-spells">
            {view.items.map((spell) => (
              <li key={spell.id} className="swl-spellbook-spell" data-swl-spell={spell.id}>
                <span className="swl-spellbook-name">{spell.name}</span>
                <span className="swl-spellbook-level">Lv {spell.level}</span>
                <span className="swl-spellbook-area">area {spell.areaForLevel}</span>
                <button
                  type="button"
                  className="swl-spellbook-cast"
                  disabled={!spell.enabled || !spell.castable}
                  onClick={() => onCommand?.(useMagic(spell.id))}
                >
                  Cast · {spell.mana} mana
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="swl-spellbook-pages" role="group" aria-label="Spell book pages">
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
