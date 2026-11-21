/**
 * A pure guard for touch gestures on the map.
 *
 * The renderer's map click is a **gesture**: the client decides which tile
 * was tapped and sends one command; the server still decides what happens.
 * A touch screen can turn one intended gesture into several pointer events —
 * a double tap, a two-finger pinch, or a finger that drags before it lifts —
 * and each of those must not become a second command.
 *
 * Nothing here knows about the DOM or the clock: callers pass the pointer
 * id, points in the canvas's own pixels, and (on release) a timestamp.
 * That keeps the rule testable in isolation and keeps it out of the game's
 * authority — the guard only decides *whether to ask*, never the answer.
 *
 * Mouse pointers do not go through this guard: the mouse keeps its original,
 * immediate click path. Only touch (and pen) input is deferred to release.
 */

/** How close two taps must be in time to count as one double tap. */
export const DOUBLE_TAP_MS = 300;

/** How far a finger may drift before the gesture is a drag, not a tap. */
export const TAP_SLOP_PX = 12;

/** A point in the canvas's own pixels. */
export interface TouchPoint {
  x: number;
  y: number;
}

export class TouchGestureGuard {
  private readonly active = new Set<number>();
  private readonly starts = new Map<number, TouchPoint>();
  private readonly dragged = new Set<number>();
  private cancelled = false;
  private lastAcceptedAt: number | null = null;
  private lastAccepted: TouchPoint | null = null;

  /** A pointer went down; only a sole, still pointer may become a tap. */
  down(id: number, point: TouchPoint): void {
    this.active.add(id);
    this.starts.set(id, point);
    this.dragged.delete(id);
    // A second pointer is a pinch. Nothing in that gesture is a tap.
    if (this.active.size > 1) this.cancelled = true;
  }

  /** A pointer moved; beyond the slop it is a drag and can no longer tap. */
  move(id: number, point: TouchPoint): void {
    const start = this.starts.get(id);
    if (!start) return;
    if (Math.hypot(point.x - start.x, point.y - start.y) > TAP_SLOP_PX) {
      this.dragged.add(id);
    }
  }

  /**
   * A pointer went up.
   *
   * Returns true **once** for a completed single tap, and false for a
   * pinch, a drag, a double tap's second tap, or an orphan release.
   */
  up(id: number, timeMs: number, point: TouchPoint): boolean {
    if (!this.active.delete(id)) return false;
    this.starts.delete(id);
    const wasDragged = this.dragged.delete(id);
    // Wait until the last finger lifts: the first finger of a pinch must
    // not fire a command before the second finger arrives.
    if (this.active.size > 0) return false;

    const wasCancelled = this.cancelled;
    this.cancelled = false;
    if (wasCancelled || wasDragged) return false;

    const since = this.lastAcceptedAt === null ? Infinity : timeMs - this.lastAcceptedAt;
    const moved =
      this.lastAccepted === null
        ? Infinity
        : Math.hypot(point.x - this.lastAccepted.x, point.y - this.lastAccepted.y);
    if (since >= 0 && since < DOUBLE_TAP_MS && moved <= TAP_SLOP_PX) {
      return false;
    }

    this.lastAcceptedAt = timeMs;
    this.lastAccepted = point;
    return true;
  }

  /** Abandon an unfinished gesture, e.g. on `pointercancel`. */
  cancel(): void {
    this.active.clear();
    this.starts.clear();
    this.dragged.clear();
    this.cancelled = false;
  }
}
