/**
 * The tutorial.
 *
 * The tutorial is a **scripted sequence of pointers**: each step names a
 * place on the screen and what the player is expected to do there. The
 * client draws an arrow at the place, a circle around it when the step
 * has one, and the mayor's box with the title and the lesson.
 *
 * The **model** is the client's own (`packages/client/src/tutorial.ts`):
 * which steps the player sees, where they are, and the client's own
 * literal text. This is the drawing of it.
 *
 * The progression is the **server's**: the client sends the step it
 * reached with `complete_tutorial`, and the server keeps the furthest
 * step. The overlay therefore never invents progress; it draws what the
 * server's step list says and asks the server to record the next one.
 */
import { tutorialLiteral, type TutorialStep } from '@swl/client';

/** The overlay's props. */
export interface TutorialOverlayProps {
  /** The step to draw. */
  step: TutorialStep;
  /** Where the step sits in this player's list, 1-based. */
  position: number;
  /** How many steps this player sees. */
  total: number;
  /** The player asked for the next step. */
  onNext: () => void;
  /** The player asked to skip the tutorial, when the step allows it. */
  onSkip?: () => void;
}

/** The stage's width and height, the client's own. */
const STAGE_WIDTH = 760;
const STAGE_HEIGHT = 600;
/** The mayor's box. */
const BOX_WIDTH = 286;
const BOX_HEIGHT = 172;

/** Keep the box inside the stage. */
function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(Math.max(value, minimum), maximum);
}

/**
 * Where the mayor's box goes.
 *
 * It sits **below** the place the step points at, so the arrow and the
 * place stay visible, and it is kept inside the stage: the client's own
 * step positions were laid out for the 760 by 600 stage and a box that
 * hangs over the edge is a box the player cannot read.
 */
function boxPosition(step: TutorialStep): { left: number; top: number } {
  const x = typeof step.x === 'number' ? step.x : STAGE_WIDTH / 2;
  const y = typeof step.y === 'number' ? step.y : STAGE_HEIGHT / 2;
  const left = clamp(x - BOX_WIDTH / 2, 6, STAGE_WIDTH - BOX_WIDTH - 6);
  const top = clamp(y + 26, 42, STAGE_HEIGHT - BOX_HEIGHT - 6);
  return { left, top };
}

/** The tutorial's overlay. */
export function TutorialOverlay({
  step,
  position,
  total,
  onNext,
  onSkip,
}: TutorialOverlayProps): React.JSX.Element {
  const title = tutorialLiteral(step.title);
  const lesson = tutorialLiteral(step.lesson);
  const box = boxPosition(step);
  const arrow =
    typeof step.ax === 'number' && typeof step.ay === 'number'
      ? { left: step.ax, top: step.ay, rotation: step.arot ?? 0 }
      : null;
  const ring =
    typeof step.cx === 'number' &&
    typeof step.cy === 'number' &&
    typeof step.cr === 'number'
      ? { left: step.cx - step.cr, top: step.cy - step.cr, size: step.cr * 2 }
      : null;

  return (
    <div className="swl-tutorial" role="dialog" aria-label="Tutorial">
      {ring ? (
        <span
          className="swl-tutorial-ring"
          style={{
            left: `${ring.left}px`,
            top: `${ring.top}px`,
            width: `${ring.size}px`,
            height: `${ring.size}px`,
          }}
          aria-hidden="true"
        />
      ) : null}
      {arrow ? (
        <span
          className="swl-tutorial-arrow"
          style={{
            left: `${arrow.left}px`,
            top: `${arrow.top}px`,
            transform: `translate(-50%, -50%) rotate(${arrow.rotation}deg)`,
          }}
          aria-hidden="true"
        />
      ) : null}
      <div
        className="swl-tutorial-box"
        style={{ left: `${box.left}px`, top: `${box.top}px` }}
      >
        <p className="swl-tutorial-step">
          STEP {position} OF {total}
        </p>
        {title ? <h2 className="swl-tutorial-title">{title}</h2> : null}
        {lesson.split('\n').map((line, index) => (
          <p key={index} className="swl-tutorial-lesson">
            {line}
          </p>
        ))}
        <div className="swl-tutorial-actions">
          {step.skippable ? (
            <button type="button" className="swl-tutorial-skip" onClick={onSkip}>
              Skip tutorial
            </button>
          ) : null}
          <button type="button" className="swl-tutorial-next" onClick={onNext}>
            {step.haveButton ? 'Continue' : 'Next'}
          </button>
        </div>
      </div>
    </div>
  );
}
