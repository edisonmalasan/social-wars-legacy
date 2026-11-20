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
  activeQuestState,
  type ArmyUnitView,
  hudState,
  levelOf,
  questChoices,
  type DialogState,
  type FeedbackMessage,
  type ItemType,
  type NativeCommand,
  type Neighbour,
  type QuestActionChoice,
  type QuestChoice,
  type QuestDifficulty,
  type StoredItemView,
  type WorldSnapshot,
} from '@swl/client';
import type { Army } from '@swl/rules';
import type { ContentBundle } from '@swl/content';

import { BuildMenu } from './buildmenu.tsx';
import { Chapters } from './chapters.tsx';
import { Dialog } from './dialog.tsx';
import { Feedback } from './feedback.tsx';
import { Goals } from './goals.tsx';
import { Hud } from './hud.tsx';
import { InfoPanel, ProductionSelector, PRODUCTION_DIALOG_ID } from './info.tsx';
import { Inventory } from './inventory.tsx';
import { Neighbours } from './neighbours.tsx';
import { QuestPanel, type QuestPanelView } from './quests.tsx';
import { RecruitPanel } from './recruit.tsx';
import { TutorialOverlay, type TutorialOverlayProps } from './tutorial.tsx';
import {
  buildingInfo,
  buildItems,
  categories,
  goalList,
  hudInput,
  infoPanel,
  inventoryItems,
  type ProductionPanelView,
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
  /** The quest panel hosted by the shared dialog, or null. */
  questPanel?: QuestPanelView | null;
  /** True while a quest request is pending. */
  questBusy?: boolean;
  /** The player asked the dialog to close. */
  onDialogDismiss?: () => void;
  /** The player picked an opened chapter slot. */
  onQuestPick?: (choice: QuestChoice) => void;
  /** The player asked to start a quest at a difficulty, with an optional team. */
  onQuestStart?: (questId: string, difficulty: QuestDifficulty, team?: Army) => void;
  /** The player pressed one of the quest's allowed actions. */
  onQuestAction?: (questId: string, action: QuestActionChoice) => void;
  /** The player asked to retry (or replay) a finished mission. */
  onQuestRetry?: (questId: string) => void;
  /** The player asked to open the next mission the server made available. */
  onQuestNext?: (questId: string) => void;
  /** The player asked to collect the selected building's production. */
  onCollect?: () => void;
  /** The player picked a stored item to place on the map. */
  onPlaceStored?: (entry: StoredItemView) => void;
  /** The army the server's save accounts for, drawn beside storage. */
  army?: readonly ArmyUnitView[];
  /** The player asked for the daily bonus; the server decides the reward. */
  onClaimBonus?: () => void | Promise<unknown>;
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
  /** The selected building's production cycle, when it can choose one. */
  production?: ProductionPanelView | null;
  /** The player asked to open the collection-period selector. */
  onOpenProduction?: () => void;
  /** The player picked one of the content's collection periods. */
  onActivate?: (period: number) => void;
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
  questPanel = null,
  questBusy = false,
  onDialogDismiss,
  onQuestPick,
  onQuestStart,
  onQuestAction,
  onQuestRetry,
  onQuestNext,
  onCollect,
  army = [],
  onPlaceStored,
  onClaimBonus,
  onPick,
  onCommand,
  onUpgrade,
  onFinish,
  onTrain,
  onTake,
  production = null,
  onOpenProduction,
  onActivate,
}: RootProps): React.JSX.Element {
  const state = hudState(hudInput(bundle, world));
  const items = useMemo(() => buildItems(bundle), [bundle]);
  const tabs = useMemo(() => categories(bundle), [bundle]);
  const placingName = useMemo(() => {
    if (placing === null || placing === undefined) return null;
    return items.find((item) => item.id === placing)?.name ?? null;
  }, [items, placing]);
  const goals = useMemo(() => goalList(bundle, world), [bundle, world]);
  const stored = useMemo(() => inventoryItems(bundle, world), [bundle, world]);
  const ranks = useMemo(() => questRanks(world), [world]);
  const minLevels = useMemo(() => questMinLevels(bundle), [bundle]);
  // The chapter slots are gestures: a slot the server has opened can be
  // picked, and the active one can resume its authoritative panel.
  const activeQuestId = activeQuestState(world)?.questId ?? null;
  const choices = useMemo(
    () => questChoices(ranks, minLevels, levelOf(world), activeQuestId),
    [ranks, minLevels, world, activeQuestId],
  );
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
      <Hud state={state} placing={placingName} onClaimBonus={onClaimBonus} />
      <Goals goals={goals} onCommand={onCommand} />
      <Inventory items={stored} army={army} onPlace={onPlaceStored} />
      <Chapters
        ranks={ranks}
        minLevels={minLevels}
        choices={choices}
        onQuestPick={onQuestPick}
      />
      <InfoPanel
        resource={panel}
        unit={unit}
        building={building}
        onCollect={onCollect}
        onUpgrade={onUpgrade}
        onFinish={onFinish}
        production={production}
        onOpenProduction={onOpenProduction}
      />
      <RecruitPanel view={recruit} onTrain={onTrain} onTake={onTake} />
      <Neighbours neighbours={neighbours} />
      {tutorial ? <TutorialOverlay {...tutorial} /> : null}
      <Feedback messages={feedback} />
      <Dialog
        state={dialog ?? CLOSED_DIALOG}
        onDismiss={onDialogDismiss ?? (() => {})}
      >
        {questPanel && onQuestStart && onQuestAction ? (
          <QuestPanel
            key={
              questPanel.kind === 'briefing'
                ? `briefing:${questPanel.briefing.questId}`
                : questPanel.kind === 'combat'
                  ? `combat:${questPanel.active.questId}`
                  : `result:${questPanel.result.kind}`
            }
            view={questPanel}
            busy={questBusy}
            onStart={onQuestStart}
            onAction={onQuestAction}
            onRetry={onQuestRetry}
            onNext={onQuestNext}
            onCancel={onDialogDismiss ?? (() => {})}
          />
        ) : null}
        {dialog?.dialog?.id === PRODUCTION_DIALOG_ID && production && onActivate ? (
          <ProductionSelector view={production} onActivate={onActivate} />
        ) : null}
      </Dialog>
      <BuildMenu
        items={items}
        categories={tabs}
        playerLevel={state.level}
        onPick={onPick ? (entry) => onPick(entry.id, entry.type) : undefined}
      />
    </div>
  );
}
