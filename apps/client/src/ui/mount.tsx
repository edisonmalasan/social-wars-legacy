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
  WorldSnapshot,
} from '@swl/client';
import type { ContentBundle } from '@swl/content';

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
  /** The selected element's map id, for its server attribute bag. */
  readonly selectedIso?: number | null;
  /** The client's unix second, for on-screen countdowns. */
  readonly now?: number;
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
          onDialogDismiss={overlays.onDialogDismiss}
          onPick={onPick}
          onCollect={onCollect}
          onCommand={onCommand}
          onUpgrade={overlays.onUpgrade}
          onFinish={overlays.onFinish}
          onTrain={overlays.onTrain}
          onTake={overlays.onTake}
        />,
      ),
  };
}
