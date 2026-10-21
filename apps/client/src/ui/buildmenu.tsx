/**
 * The build menu.
 *
 * The panel where the player buys the buildings and the units. The
 * **model** is the client's own (`packages/client/src/buildmenu.ts`): the
 * tabs, the order, which entries are locked and the costs. This is the
 * drawing of it.
 */
import { useState } from 'react';

import {
  buildMenu,
  buildTabs,
  type BuildMenuEntry,
  type BuildMenuItem,
} from '@swl/client';

/** The build menu's props. */
export interface BuildMenuProps {
  /** Every item the content has. */
  items: readonly BuildMenuItem[];
  /** The categories, from the content. */
  categories: Record<
    string,
    { id: number; name: string; sub?: { id: number; name: string }[] }
  >;
  /** The player's level, which decides what is locked. */
  playerLevel: number;
  /** The player picked an item. */
  onPick?: (item: BuildMenuEntry) => void;
}

/** The cost, written the way the client writes it. */
function costText(entry: BuildMenuEntry): string {
  const parts: string[] = [];
  for (const [key, value] of Object.entries(entry.costs)) {
    if (!value) continue;
    parts.push(`${value} ${key}`);
  }
  return parts.join(' · ');
}

/**
 * The build menu.
 *
 * The tabs are the client's, and so is the order: the entries the player
 * cannot build yet go **down** the list rather than disappearing, so the
 * player can see what is coming.
 */
export function BuildMenu({
  items,
  categories,
  playerLevel,
  onPick,
}: BuildMenuProps): React.JSX.Element {
  const tabs = buildTabs(categories);
  const [tab, setTab] = useState<number | undefined>(undefined);
  const entries = buildMenu(items, playerLevel, tab);

  return (
    <div className="swl-build-menu">
      <nav className="swl-build-tabs">
        <button
          type="button"
          className={tab === undefined ? 'swl-tab swl-tab-active' : 'swl-tab'}
          onClick={() => setTab(undefined)}
        >
          All
        </button>
        {tabs.map((entry) => (
          <button
            key={entry.id}
            type="button"
            className={entry.id === tab ? 'swl-tab swl-tab-active' : 'swl-tab'}
            onClick={() => setTab(entry.id)}
          >
            {entry.name}
          </button>
        ))}
      </nav>
      <ul className="swl-build-list">
        {entries.map((entry) => (
          <li
            key={entry.id}
            className={entry.locked ? 'swl-build-item swl-build-locked' : 'swl-build-item'}
          >
            <button type="button" onClick={() => onPick?.(entry)}>
              <span className="swl-build-name">{entry.name}</span>
              <span className="swl-build-cost">{costText(entry)}</span>
              {entry.locked ? (
                <span className="swl-build-lock">level {entry.minLevel}</span>
              ) : null}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
