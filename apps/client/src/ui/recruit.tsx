/**
 * The recruitment panel.
 *
 * The card a training building shows: one Train button per unit the content
 * lets it make, the server's queue (count, current unit and countdown) and a
 * Take button that is only usable when the server's queue says a unit is
 * finished. Every value is a reading of the world answer and the content;
 * the panel never decides a cost, an outcome or a resource change.
 */
import type { RecruitView } from '@swl/client';

import { TrainingQueuePortraits } from './unitportraits.tsx';

/** The recruitment panel's props. */
export interface RecruitPanelProps {
  /** The derived view, or null when the selection is not a training building. */
  view: RecruitView | null;
  /** The player asked to train the named unit. */
  onTrain?: (unitItemId: number) => void;
  /** The player asked to take the finished unit out of the queue. */
  onTake?: () => void;
}

/**
 * The recruitment panel, or nothing when no training building is selected.
 *
 * The Take button is disabled until the queue's own `readyToTake` flag is
 * set, so the client does not offer a command the server would refuse as
 * "still-training". The countdown is a presentation of the server's `ts`
 * and the content's training time.
 */
export function RecruitPanel({
  view,
  onTrain,
  onTake,
}: RecruitPanelProps): React.JSX.Element | null {
  if (!view) return null;
  const { queue } = view;
  return (
    <div className="swl-recruit">
      <div className="swl-recruit-title">Recruit · {view.buildingName}</div>
      {view.units.length > 0 ? (
        <ul className="swl-recruit-units">
          {view.units.map((unit) => (
            <li className="swl-recruit-unit" key={unit.itemId}>
              <span className="swl-recruit-unit-name">{unit.name}</span>
              <button
                type="button"
                className="swl-recruit-train"
                onClick={() => onTrain?.(unit.itemId)}
              >
                Train
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      <div className="swl-recruit-queue">
        <TrainingQueuePortraits queue={view.queue} units={view.units} />
        <span className="swl-recruit-countdown">
          {queue.queued <= 0
            ? 'No units queued'
            : queue.readyToTake
              ? `Unit ready · ${queue.queued} queued`
              : `Training · ${queue.remainingSeconds}s left (${queue.queued} queued)`}
        </span>
        <button
          type="button"
          className="swl-recruit-take"
          disabled={!queue.readyToTake}
          onClick={() => onTake?.()}
        >
          Take unit
        </button>
      </div>
    </div>
  );
}
