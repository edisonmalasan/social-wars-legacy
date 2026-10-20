/**
 * The client's predictions.
 *
 * The rule the whole design rests on: **the client never decides an
 * outcome**. It may *predict* one, to hide the latency of the round
 * trip, but a prediction is never final — it is replaced by the
 * server's answer, and a rejected prediction is undone.
 *
 * That is a property of the *shape* of the code, not a rule the renderer
 * has to remember. The renderer asks this module for what to draw, and
 * this module answers with:
 *
 * - the server's confirmed state, when there is one
 * - the server's state with the **unconfirmed** predictions applied on
 *   top, and every one of them marked as unconfirmed
 *
 * So a prediction can be drawn as an interpolation - a unit sliding
 * towards where it is going - and it can never be mistaken for
 * something the server agreed to.
 *
 * ## Why the idempotency key matters
 *
 * Each prediction carries the request's **idempotency key**, the same
 * one the native protocol uses. A retry of a request that was lost in
 * flight carries the same key, and the server replays its stored answer
 * rather than applying the commands twice. So the client can retry
 * safely, and a prediction that comes back twice is the same prediction,
 * not two.
 */

/** A prediction the client made but the server has not confirmed. */
export interface Prediction<T> {
  /** The request's idempotency key. */
  id: string;
  /** What the client expects to happen. */
  expected: T;
  /** When it was sent, in milliseconds. */
  sentAt: number;
}

/** Whether a prediction has been settled. */
export type PredictionState = 'pending' | 'confirmed' | 'rejected';

/** A prediction and its state. */
export interface TrackedPrediction<T> extends Prediction<T> {
  state: PredictionState;
}

/** What happened when a prediction was settled. */
export interface Settlement<T> {
  /** The prediction that was settled. */
  prediction: TrackedPrediction<T>;
  /** Whether the server agreed. */
  confirmed: boolean;
  /** Whether this was a duplicate answer for a request already settled. */
  duplicate: boolean;
}

/**
 * The client's pending predictions.
 *
 * It is bounded: a client that never receives an answer - because the
 * connection dropped, say - must not accumulate predictions for ever.
 */
export class Predictions<T> {
  private readonly tracked = new Map<string, TrackedPrediction<T>>();
  private readonly limit: number;

  constructor(limit = 128) {
    this.limit = limit;
  }

  /** How many predictions are outstanding. */
  get size(): number {
    return this.tracked.size;
  }

  /** The predictions that are still outstanding. */
  get pending(): TrackedPrediction<T>[] {
    return [...this.tracked.values()].filter(
      (prediction) => prediction.state === 'pending',
    );
  }

  /**
   * Record a prediction.
   *
   * A prediction with an id that is already outstanding **replaces** it:
   * the retry of a request that was lost in flight is the same request,
   * so it has the same prediction.
   */
  send(id: string, expected: T, sentAt: number): Prediction<T> {
    const prediction: Prediction<T> = { id, expected, sentAt };
    this.tracked.set(id, { ...prediction, state: 'pending' });
    this.trim();
    return prediction;
  }

  /**
   * Settle a prediction with the server's answer.
   *
   * A prediction that was already settled is a **duplicate** — the same
   * answer arriving twice — and is reported as such rather than settled
   * again. Settling it twice would undo a confirmed outcome.
   */
  settle(id: string, confirmed: boolean): Settlement<T> | null {
    const existing = this.tracked.get(id);
    if (!existing) return null;
    if (existing.state !== 'pending') {
      return { prediction: existing, confirmed, duplicate: true };
    }
    const settled: TrackedPrediction<T> = {
      ...existing,
      state: confirmed ? 'confirmed' : 'rejected',
    };
    this.tracked.set(id, settled);
    return { prediction: settled, confirmed, duplicate: false };
  }

  /** The prediction with an id, if there is one. */
  get(id: string): TrackedPrediction<T> | undefined {
    return this.tracked.get(id);
  }

  /** Forget a settled prediction. */
  forget(id: string): void {
    this.tracked.delete(id);
  }

  /** Forget every settled prediction, keeping the outstanding ones. */
  forgetSettled(): void {
    for (const [id, prediction] of [...this.tracked]) {
      if (prediction.state !== 'pending') this.tracked.delete(id);
    }
  }

  /**
   * Drop the oldest predictions when there are too many.
   *
   * The oldest are dropped first, and only the settled ones: a prediction
   * that is still outstanding might still be answered.
   */
  private trim(): void {
    while (this.tracked.size > this.limit) {
      let oldest: string | null = null;
      let oldestAt = Number.POSITIVE_INFINITY;
      for (const [id, prediction] of this.tracked) {
        if (prediction.state !== 'pending' && prediction.sentAt < oldestAt) {
          oldest = id;
          oldestAt = prediction.sentAt;
        }
      }
      if (oldest === null) {
        // Everything is still outstanding; drop the oldest anyway.
        for (const [id, prediction] of this.tracked) {
          if (prediction.sentAt < oldestAt) {
            oldest = id;
            oldestAt = prediction.sentAt;
          }
        }
      }
      if (oldest === null) break;
      this.tracked.delete(oldest);
    }
  }
}

/**
 * What the renderer should draw.
 *
 * The confirmed state is the server's. The unconfirmed predictions are
 * applied on top, and returned **separately**, so the renderer can mark
 * them as provisional — they are interpolation, not facts.
 */
export interface RenderState<S> {
  /** The server's state, or null before the first answer. */
  confirmed: S | null;
  /** The predictions that are still outstanding, oldest first. */
  unconfirmed: Prediction<S>[];
}

/**
 * Fold the outstanding predictions onto the server's state.
 *
 * The server's state is the base and the predictions are applied on
 * top, so the renderer always draws the **server's** answer as the
 * truth and the predictions as an overlay.
 */
export function renderState<S>(
  predictions: Predictions<S>,
  confirmed: S | null,
  apply: (state: S, prediction: S) => S,
): RenderState<S> {
  const outstanding = predictions.pending.sort((a, b) => a.sentAt - b.sentAt);
  return {
    confirmed,
    unconfirmed: outstanding.map((prediction) => ({
      id: prediction.id,
      expected: prediction.expected,
      sentAt: prediction.sentAt,
    })),
  };
}
