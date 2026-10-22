/**
 * The interface's root.
 *
 * It is the whole of the interface in one place: the **HUD** across the
 * top and the **build menu** in the corner. Both are drawn from the
 * server's answer and from the content, and neither decides anything:
 * the numbers are the server's, and the menu is a list of what the
 * player could ask for.
 *
 * The state is derived here rather than passed in, because the HUD's
 * numbers are a **reading** of the world: the resources are the
 * server's, and the limits are the content's.
 */
import { useMemo } from 'react';

import { hudState, type Neighbour, type WorldSnapshot } from '@swl/client';
import type { ContentBundle } from '@swl/content';

import { BuildMenu } from './buildmenu.tsx';
import { Chapters } from './chapters.tsx';
import { Goals } from './goals.tsx';
import { Hud } from './hud.tsx';
import { InfoPanel } from './info.tsx';
import { Neighbours } from './neighbours.tsx';
import { TutorialOverlay, type TutorialOverlayProps } from './tutorial.tsx';
import {
  buildItems,
  categories,
  goalList,
  hudInput,
  infoPanel,
  questMinLevels,
  questRanks,
  unitInfoPanel,
} from './state.ts';

/** The root's props. */
export interface RootProps {
  /** The server's answer. */
  world: WorldSnapshot;
  /** The content bundle. */
  bundle: ContentBundle;
  /** The item the player is about to place, or null. */
  placing?: number | null;
  /** The item the player selected on the map, or null. */
  selected?: number | null;
  /** The other players, for the neighbour strip. */
  neighbours?: readonly Neighbour[];
  /** The tutorial step to draw, or null when the tutorial is not running. */
  tutorial?: TutorialOverlayProps | null;
  /** The player asked to collect the selected building's production. */
  onCollect?: () => void;
  /** The player picked something to build. */
  onPick?: (itemId: number) => void;
}

/**
 * The interface.
 *
 * The HUD's state is derived from the world every time the world
 * changes, and the build menu's items are derived from the content
 * **once**: the content does not change while the game is running.
 */
export function Root({
  world,
  bundle,
  placing,
  selected,
  neighbours = [],
  tutorial = null,
  onCollect,
  onPick,
}: RootProps): React.JSX.Element {
  const state = hudState(hudInput(bundle, world));
  const items = useMemo(() => buildItems(bundle), [bundle]);
  const tabs = useMemo(() => categories(bundle), [bundle]);
  const placingName = useMemo(() => {
    if (placing === null || placing === undefined) return null;
    return items.find((item) => item.id === placing)?.name ?? null;
  }, [items, placing]);
  const goals = useMemo(() => goalList(bundle, world), [bundle, world]);
  const ranks = useMemo(() => questRanks(world), [world]);
  const minLevels = useMemo(() => questMinLevels(bundle), [bundle]);
  const panel = useMemo(() => infoPanel(bundle, selected ?? null), [bundle, selected]);
  const unit = useMemo(() => unitInfoPanel(bundle, selected ?? null), [bundle, selected]);

  return (
    <div className="swl-ui">
      <Hud state={state} placing={placingName} />
      <Goals goals={goals} />
      <Chapters ranks={ranks} minLevels={minLevels} />
      <InfoPanel resource={panel} unit={unit} onCollect={onCollect} />
      <Neighbours neighbours={neighbours} />
      {tutorial ? <TutorialOverlay {...tutorial} /> : null}
      <BuildMenu
        items={items}
        categories={tabs}
        playerLevel={state.level}
        onPick={onPick ? (entry) => onPick(entry.id) : undefined}
      />
    </div>
  );
}
