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

import {
  CLOSED_DIALOG,
  hudState,
  type DialogState,
  type FeedbackMessage,
  type ItemType,
  type NativeCommand,
  type Neighbour,
  type WorldSnapshot,
} from '@swl/client';
import type { ContentBundle } from '@swl/content';

import { BuildMenu } from './buildmenu.tsx';
import { Chapters } from './chapters.tsx';
import { Dialog } from './dialog.tsx';
import { Feedback } from './feedback.tsx';
import { Goals } from './goals.tsx';
import { Hud } from './hud.tsx';
import { InfoPanel } from './info.tsx';
import { Neighbours } from './neighbours.tsx';
import { RecruitPanel } from './recruit.tsx';
import { TutorialOverlay, type TutorialOverlayProps } from './tutorial.tsx';
import {
  buildingInfo,
  buildItems,
  categories,
  goalList,
  hudInput,
  infoPanel,
  questMinLevels,
  questRanks,
  recruitView,
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
  /** The map id of the selected element, for its server attribute bag. */
  selectedIso?: number | null;
  /** The client's unix second, used only for on-screen countdowns. */
  now?: number;
  /** The other players, for the neighbour strip. */
  neighbours?: readonly Neighbour[];
  /** The tutorial step to draw, or null when the tutorial is not running. */
  tutorial?: TutorialOverlayProps | null;
  /** The one open dialog, or null when none is open. */
  dialog?: DialogState | null;
  /** The feedback messages read from the server's last answer. */
  feedback?: readonly FeedbackMessage[];
  /** The player asked the dialog to close. */
  onDialogDismiss?: () => void;
  /** The player asked to collect the selected building's production. */
  onCollect?: () => void;
  /** The player picked something to build, with its real wire type. */
  onPick?: (itemId: number, type: ItemType) => void;
  /** The player claimed a goal; send it through the client's transport. */
  onCommand?: (command: NativeCommand) => void;
  /** The player asked to upgrade the selected building. */
  onUpgrade?: () => void;
  /** The player asked to hurry the selected building's construction. */
  onFinish?: () => void;
  /** The player asked to train a unit in the selected building. */
  onTrain?: (unitItemId: number) => void;
  /** The player asked to take the finished unit out of the queue. */
  onTake?: () => void;
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
  selectedIso = null,
  now = Math.floor(Date.now() / 1000),
  neighbours = [],
  tutorial = null,
  dialog = null,
  feedback = [],
  onDialogDismiss,
  onCollect,
  onPick,
  onCommand,
  onUpgrade,
  onFinish,
  onTrain,
  onTake,
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
  const building = useMemo(
    () => buildingInfo(bundle, world, selectedIso, now),
    [bundle, world, selectedIso, now],
  );
  const recruit = useMemo(
    () => recruitView(bundle, world, selectedIso, now),
    [bundle, world, selectedIso, now],
  );

  return (
    <div className="swl-ui">
      <Hud state={state} placing={placingName} />
      <Goals goals={goals} onCommand={onCommand} />
      <Chapters ranks={ranks} minLevels={minLevels} />
      <InfoPanel
        resource={panel}
        unit={unit}
        building={building}
        onCollect={onCollect}
        onUpgrade={onUpgrade}
        onFinish={onFinish}
      />
      <RecruitPanel view={recruit} onTrain={onTrain} onTake={onTake} />
      <Neighbours neighbours={neighbours} />
      {tutorial ? <TutorialOverlay {...tutorial} /> : null}
      <Feedback messages={feedback} />
      <Dialog
        state={dialog ?? CLOSED_DIALOG}
        onDismiss={onDialogDismiss ?? (() => {})}
      />
      <BuildMenu
        items={items}
        categories={tabs}
        playerLevel={state.level}
        onPick={onPick ? (entry) => onPick(entry.id, entry.type) : undefined}
      />
    </div>
  );
}
