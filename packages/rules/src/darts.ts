/**
 * The darts minigame schedule.
 *
 * The upstream server rotates the darts dates at *startup* so the weekly prize
 * rotation stays current. That is why `config/main.json` has 2012 dates and the
 * running server has 2026 ones.
 *
 * A content bundle must stay reproducible, so the rotation cannot happen at
 * build time. It happens here, at runtime, from the bundle's static dates.
 *
 * The rotation is the upstream's `make_dynamic` / `update_darts`, ported:
 * the schedule advances in whole weeks, each game lasts exactly 7 days from
 * the first one, and the dates are snapped to Mondays.
 *
 * **The schedule is worked in UTC.** The upstream does it in the server's
 * local time, which makes the result depend on the machine's timezone: two
 * servers in different zones would rotate to different strings. The strings
 * are what the client shows, so they have to be the same everywhere, and UTC
 * is what makes them so. It also removes the daylight-saving correction the
 * upstream needed, because UTC has no daylight saving.
 */

const WEEK_SECONDS = 604800;
const WEEK_MS = WEEK_SECONDS * 1000;
const DAY_SECONDS = 86400;

export interface DartsGame {
  id: number;
  start_date: string;
  extra_item: number;
  items: number[];
}

/** The date format the config uses. */
const DATE_FORMAT = 'YYYY-MM-DD HH:mm:ss';

/**
 * Parse a schedule date.
 *
 * The string is a **UTC** wall clock, not a local one. The local-time
 * constructor is what made the schedule depend on the machine's timezone.
 */
function parseDate(value: string): Date {
  const match = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})$/.exec(value);
  if (!match) throw new Error(`unparsable darts date: ${value}`);
  return new Date(
    Date.UTC(
      Number(match[1]),
      Number(match[2]) - 1,
      Number(match[3]),
      Number(match[4]),
      Number(match[5]),
      Number(match[6]),
    ),
  );
}

/** Format a schedule date, as a UTC wall clock. */
function formatDate(date: Date): string {
  const pad = (n: number): string => String(n).padStart(2, '0');
  return (
    `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} ` +
    `${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:${pad(date.getUTCSeconds())}`
  );
}

/** The Monday of the week containing `date`, at midnight. */
function mondayOf(date: Date): Date {
  const day = date.getUTCDay(); // 0 = Sunday
  const delta = day === 0 ? -6 : 1 - day;
  const monday = new Date(date);
  monday.setUTCDate(monday.getUTCDate() + delta);
  monday.setUTCHours(0, 0, 0, 0);
  return monday;
}

/**
 * Rotate the darts schedule so it is current at `now`.
 *
 * The upstream advances the whole schedule forward in 7-day steps until the
 * last game is in the future, and rewrites every game's start date so each one
 * is exactly 7 days after the previous. The games keep their relative order and
 * their prizes.
 */
export function rotateDartsSchedule(
  games: readonly DartsGame[],
  now: Date,
): DartsGame[] {
  if (games.length === 0) return [];

  const out = games.map((game) => ({ ...game }));
  const first = parseDate(out[0]!.start_date);
  // Anchor the schedule on the Monday of the current week, so the rotation is
  // stable within a week and changes on Mondays, exactly like the upstream.
  const anchor = mondayOf(now);

  for (let i = 0; i < out.length; i++) {
    const start = new Date(anchor.getTime() + i * WEEK_MS);
    out[i]!.start_date = formatDate(start);
  }
  return out;
}

/**
 * The darts game that is live at `now`.
 *
 * The upstream wraps the schedule forward until the last game starts in the
 * future, which means the *last* game in the list is the one running.
 */
export function currentDartsGame(
  games: readonly DartsGame[],
  now: Date,
): DartsGame | null {
  if (games.length === 0) return null;
  const rotated = rotateDartsSchedule(games, now);
  for (let i = rotated.length - 1; i >= 0; i--) {
    const start = parseDate(rotated[i]!.start_date);
    if (start.getTime() <= now.getTime()) return rotated[i]!;
  }
  return rotated[0]!;
}

/** The number of whole weeks between two dates. */
export function weeksBetween(a: Date, b: Date): number {
  return Math.floor((b.getTime() - a.getTime()) / WEEK_MS);
}

export { WEEK_SECONDS, WEEK_MS, DAY_SECONDS, DATE_FORMAT };
