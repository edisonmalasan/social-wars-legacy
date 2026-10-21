/**
 * The interface's mounting.
 *
 * The React tree is mounted **once** and then **redrawn** from each
 * answer the server sends, so the interface and the scene always show
 * the same world: the numbers in the top bar and the buildings on the
 * map are one answer, drawn twice.
 */
import { createRoot } from 'react-dom/client';
import type { WorldSnapshot } from '@swl/client';
import type { ContentBundle } from '@swl/content';

import { Root } from './root.tsx';

/** The mounted interface. */
export interface UiHandle {
  /** Draw the interface from the server's answer. */
  draw: (world: WorldSnapshot) => void;
}

/** Mount the interface into an element. */
export function mountUi(element: HTMLElement, bundle: ContentBundle): UiHandle {
  const root = createRoot(element);
  return {
    draw: (world) => root.render(<Root world={world} bundle={bundle} />),
  };
}
