/**
 * The darts board.
 *
 * The minigame is a board of **25 balloons**, and shooting one discovers a
 * prize. Six prizes are on the board and one extra is hidden, and the extra
 * is won by discovering **all six** — once.
 *
 * ## The board
 *
 * From `popups/PopupDarts.as:40-41` and `initTargetItems`:
 *
 * ```as3
 * private static const NUM_TARGETS:int = 25;
 * private static const NUM_ITEMS:int = 6;
 *
 * targetItemIndices.push(0);            // 1 target
 * targetItemIndices.push(1);            // 1 target
 * for (i = 0; i < 4; i++) { push(2); push(3); }   // 4 targets each
 * for (i = 0; i < 7; i++) { push(4); }             // 7 targets
 * for (i = 0; i < 8; i++) { push(5); }             // 8 targets
 * ```
 *
 * So the prizes are spread **1, 1, 4, 4, 7, 8** over the 25 targets, and
 * the balloons shuffle while they float. The shuffle is seeded by
 * `dartsRandomSeed`, which the **server** sends, so every player sees the
 * same board that week.
 *
 * ## The shot
 *
 * The first shot of the day is **free** (`dartsHasFree`), and every shot
 * after it costs **20 cash** (`Config.DART_COST_CASH`). The shots already
 * made are recorded in `dartsBalloonsShot`.
 *
 * ## The extra prize
 *
 * ```as3
 * if(!Base.Player.dartsGotExtra && this.allDiscovered()) { ... the extra item ... }
 * ```
 *
 * `allDiscovered()` is true when all **six** prizes have been found, and
 * `dartsGotExtra` makes it once only.
 */
import { Random } from './random.ts';

/** How many balloons are on the board. `PopupDarts.NUM_TARGETS`. */
export const NUM_TARGETS = 25;

/** How many prizes are on the board. `PopupDarts.NUM_ITEMS`. */
export const NUM_PRIZES = 6;

/**
 * How many targets carry each prize.
 *
 * The client builds the list in this order, so the rarest prizes are the
 * fewest targets.
 */
export const PRIZE_TARGET_COUNTS: readonly number[] = [1, 1, 4, 4, 7, 8];

/** The cash a shot that is not free costs. `Config.DART_COST_CASH`. */
export const DART_COST_CASH = 20;

/** The board's state. */
export interface DartsState {
  /** The seed the board was built from. */
  seed: number;
  /** The prize index on each of the 25 targets. */
  board: readonly number[];
  /** The indices of the targets already shot. */
  shot: readonly number[];
  /** Whether the player still has a free shot. */
  hasFree: boolean;
  /** Whether the extra prize has been won. */
  gotExtra: boolean;
  /** Which of the six prizes have been discovered. */
  discovered: readonly boolean[];
}

/**
 * Build the board for a seed.
 *
 * The prizes are laid out in the client's order and then shuffled, so the
 * board is the same for every player that week and different from week to
 * week.
 */
export function buildDartsBoard(seed: number): number[] {
  const board: number[] = [];
  for (let prize = 0; prize < PRIZE_TARGET_COUNTS.length; prize++) {
    for (let count = 0; count < PRIZE_TARGET_COUNTS[prize]!; count++) {
      board.push(prize);
    }
  }
  if (board.length !== NUM_TARGETS) {
    throw new Error(
      `the prize counts add up to ${board.length}, and the board has ${NUM_TARGETS} targets`,
    );
  }

  // The client's balloons shuffle while they float. The server's seed makes
  // that shuffle the same for everyone.
  const random = new Random(seed);
  for (let index = board.length - 1; index > 0; index--) {
    const other = random.int(0, index);
    const swap = board[index]!;
    board[index] = board[other]!;
    board[other] = swap;
  }
  return board;
}

/** A fresh state for a seed. */
export function newDartsState(seed: number, hasFree = true): DartsState {
  return {
    seed,
    board: buildDartsBoard(seed),
    shot: [],
    hasFree,
    gotExtra: false,
    discovered: new Array<boolean>(NUM_PRIZES).fill(false),
  };
}

/** The result of a shot. */
export interface DartsShot {
  /** The state after the shot. */
  state: DartsState;
  /** The prize the target carried, or null when the target was empty. */
  prizeIndex: number | null;
  /** The item the prize is. */
  prizeItemId: number | null;
  /** Whether this shot won the extra prize. */
  wonExtra: boolean;
  /** Whether the shot was free. */
  free: boolean;
}

/**
 * Shoot a target.
 *
 * The state is returned rather than modified, so a caller can roll it back
 * if the shot turns out to be invalid.
 */
export function shootDarts(
  state: DartsState,
  targetIndex: number,
  items: readonly number[],
  extraItemId: number,
): DartsShot {
  if (targetIndex < 0 || targetIndex >= state.board.length) {
    return {
      state,
      prizeIndex: null,
      prizeItemId: null,
      wonExtra: false,
      free: false,
    };
  }
  if (state.shot.includes(targetIndex)) {
    // The target has already been shot.
    return {
      state,
      prizeIndex: null,
      prizeItemId: null,
      wonExtra: false,
      free: false,
    };
  }

  const prizeIndex = state.board[targetIndex]!;
  const shot = [...state.shot, targetIndex];
  const discovered = [...state.discovered];
  discovered[prizeIndex] = true;

  // The extra prize is won when every prize has been discovered, and only
  // once.
  const allDiscovered = discovered.every((found) => found);
  const wonExtra = allDiscovered && !state.gotExtra;

  return {
    state: {
      ...state,
      shot,
      discovered,
      gotExtra: state.gotExtra || wonExtra,
      // The first shot is free; after it, every shot costs.
      hasFree: false,
    },
    prizeIndex,
    prizeItemId: items[prizeIndex] ?? null,
    wonExtra,
    free: state.hasFree,
  };
}

/**
 * The cash a shot costs.
 *
 * The first shot of the day is free.
 */
export function dartsShotCost(state: DartsState): number {
  return state.hasFree ? 0 : DART_COST_CASH;
}

/**
 * Whether the player has discovered every prize.
 *
 * The client's `allDiscovered`.
 */
export function allDiscovered(state: DartsState): boolean {
  return state.discovered.every((found) => found);
}

/** The extra prize's item, when the shot won it. */
export function extraPrizeItemId(wonExtra: boolean, extraItemId: number): number | null {
  return wonExtra ? extraItemId : null;
}
