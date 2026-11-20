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
  onPick?: (itemId: number) => void,
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
          neighbours={neighbours}
          tutorial={tutorial}
          dialog={overlays.dialog}
          feedback={overlays.feedback}
          onDialogDismiss={overlays.onDialogDismiss}
          onPick={onPick}
          onCollect={onCollect}
          onCommand={onCommand}
        />,
      ),
  };
}
