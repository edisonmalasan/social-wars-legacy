/**
 * The interface's mounting.
 *
 * The React tree is mounted **once** and then **redrawn** from each
 * answer the server sends, so the interface and the scene always show
 * the same world: the numbers in the top bar and the buildings on the
 * map are one answer, drawn twice.
 */
import { createRoot } from 'react-dom/client';
import type {
  DialogState,
  FeedbackMessage,
  ItemType,
  NativeCommand,
  Neighbour,
  QuestActionChoice,
  QuestChoice,
  QuestDifficulty,
  StoredItemView,
  WorldSnapshot,
} from '@swl/client';
import type { ContentBundle } from '@swl/content';

import type { QuestPanelView } from './quests.tsx';
import { Root } from './root.tsx';
import type { TutorialOverlayProps } from './tutorial.tsx';

/** The parts of the interface that are not a reading of the world. */
export interface UiOverlayState {
  /** The one open dialog, or null when none is open. */
  readonly dialog?: DialogState | null;
  /** The feedback messages read from the server's last answer. */
  readonly feedback?: readonly FeedbackMessage[];
  /** The player asked the dialog to close. */
  readonly onDialogDismiss?: () => void;
  /** The quest panel hosted by the shared dialog, or null. */
  readonly questPanel?: QuestPanelView | null;
  /** True while a quest request is pending; the request buttons are disabled. */
  readonly questBusy?: boolean;
  /** The player picked an opened chapter slot. */
  readonly onQuestPick?: (choice: QuestChoice) => void;
  /** The player asked to start a quest. */
  readonly onQuestStart?: (questId: string, difficulty: QuestDifficulty) => void;
  /** The player pressed a quest action. */
  readonly onQuestAction?: (questId: string, action: QuestActionChoice) => void;
  /** The selected element's map id, for its server attribute bag. */
  readonly selectedIso?: number | null;
  /** The client's unix second, for on-screen countdowns. */
  readonly now?: number;
  /** The player picked a stored item to place on the map. */
  readonly onPlaceStored?: (entry: StoredItemView) => void;
  /** The player asked for the daily bonus. */
  readonly onClaimBonus?: () => void | Promise<unknown>;
  /** The player asked to upgrade the selected building. */
  readonly onUpgrade?: () => void;
  /** The player asked to hurry the selected building's construction. */
  readonly onFinish?: () => void;
  /** The player asked to train a unit in the selected building. */
  readonly onTrain?: (unitItemId: number) => void;
  /** The player asked to take the finished unit out of the queue. */
  readonly onTake?: () => void;
}

/** The mounted interface. */
export interface UiHandle {
  /** Draw the interface from the server's answer. */
  draw: (
    world: WorldSnapshot,
    placing?: number | null,
    selected?: number | null,
    neighbours?: readonly Neighbour[],
    tutorial?: TutorialOverlayProps | null,
    overlays?: UiOverlayState,
  ) => void;
}

/** Mount the interface into an element. */
export function mountUi(
  element: HTMLElement,
  bundle: ContentBundle,
  onPick?: (itemId: number, type: ItemType) => void,
  onCollect?: () => void,
  onCommand?: (command: NativeCommand) => void,
): UiHandle {
  const root = createRoot(element);
  return {
    draw: (
      world,
      placing = null,
      selected = null,
      neighbours = [],
      tutorial = null,
      overlays = {},
    ) =>
      root.render(
        <Root
          world={world}
          bundle={bundle}
          placing={placing}
          selected={selected}
          selectedIso={overlays.selectedIso}
          now={overlays.now}
          neighbours={neighbours}
          tutorial={tutorial}
          dialog={overlays.dialog}
          feedback={overlays.feedback}
          questPanel={overlays.questPanel}
          questBusy={overlays.questBusy}
          onDialogDismiss={overlays.onDialogDismiss}
          onQuestPick={overlays.onQuestPick}
          onQuestStart={overlays.onQuestStart}
          onQuestAction={overlays.onQuestAction}
          onPick={onPick}
          onCollect={onCollect}
          onCommand={onCommand}
          onPlaceStored={overlays.onPlaceStored}
          onClaimBonus={overlays.onClaimBonus}
          onUpgrade={overlays.onUpgrade}
          onFinish={overlays.onFinish}
          onTrain={overlays.onTrain}
          onTake={overlays.onTake}
        />,
      ),
  };
}
