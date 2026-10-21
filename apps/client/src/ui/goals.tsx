/**
 * The goal panel.
 *
 * The panel with the player's three goals. The **model** is the client's
 * own (`packages/client/src/guidance.ts`): which goals are active, and
 * which of the three slots carries the "CLICK HERE!" badge. This is the
 * drawing of it.
 *
 * The goals are the content's and the player's progress is the server's,
 * so the panel shows what the server says and nothing more.
 */
import { useState } from 'react';

import {
  CLICK_HERE_LABEL,
  MARKER_SLOTS,
  activeGoals,
  markedGoals,
} from '@swl/client';

import type { GoalEntry } from './state.ts';

/** The goal panel's props. */
export interface GoalsProps {
  /** The player's goals, in the content's order. */
  goals: readonly GoalEntry[];
  /** Whether the tutorial is running, which hides the badges. */
  tutorialMode?: boolean;
  /** Whether the first badge has been clicked. */
  firstMarkerClicked?: boolean;
}

/**
 * The goal panel.
 *
 * The slots are the client's: three of them, and the badges are on the
 * goals the player has **not visited** — the client's own rule, down to
 * its quirk, which the model's marker slots reproduce.
 */
export function Goals({
  goals,
  tutorialMode = false,
  firstMarkerClicked = false,
}: GoalsProps): React.JSX.Element {
  const [clicked, setClicked] = useState(firstMarkerClicked);
  const active = activeGoals(goals, 0, MARKER_SLOTS);
  const marked = markedGoals(goals, {
    tutorialMode,
    firstMarkerClicked: clicked,
  });
  const titles = new Map(goals.map((goal) => [goal.index, goal.title]));

  return (
    <div className="swl-goals">
      {Array.from({ length: MARKER_SLOTS }, (_, slot) => {
        const goal = active[slot];
        const badge = marked.find((entry) => entry.slot === slot);
        return (
          <div key={slot} className="swl-goal-slot">
            {goal ? (
              <>
                <button
                  type="button"
                  className="swl-goal-title"
                  onClick={() => {
                    // The client's quirk: the first badge suppresses
                    // all three, the others suppress only their own.
                    if (badge) setClicked(true);
                  }}
                >
                  {titles.get(goal.index) ?? ''}
                </button>
                {badge ? (
                  <span className="swl-goal-badge">{CLICK_HERE_LABEL}</span>
                ) : null}
              </>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
