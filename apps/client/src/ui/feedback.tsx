/**
 * The feedback channel.
 *
 * A server refusal used to be silent: `run()` read the answer, redrew the
 * world and threw the outcomes away. This region draws the sentences the
 * pure model makes from those outcomes. Successes are `role="status"`
 * (polite); refusals are `role="alert"` (assertive), so a player using a
 * screen reader hears why the server said no.
 *
 * It is a **reading** of the server's answer. Nothing here can grant a
 * reward, spend a resource or advance a quest — the server stays the
 * authority.
 */
import type { FeedbackMessage } from '@swl/client';

/** The feedback region's props. */
export interface FeedbackProps {
  /** The messages to draw, in the order the server produced them. */
  readonly messages: readonly FeedbackMessage[];
}

/** The feedback region, or nothing when there is nothing to say. */
export function Feedback({ messages }: FeedbackProps): React.JSX.Element | null {
  if (messages.length === 0) return null;
  return (
    <div className="swl-feedback">
      {messages.map((message, index) => (
        <div
          key={index}
          className={`swl-feedback-item swl-feedback-${message.tone}`}
          role={message.tone === 'error' ? 'alert' : 'status'}
        >
          <span className="swl-feedback-mark" aria-hidden="true">
            {message.tone === 'error' ? '!' : '✓'}
          </span>
          <span className="swl-feedback-text">{message.text}</span>
        </div>
      ))}
    </div>
  );
}
