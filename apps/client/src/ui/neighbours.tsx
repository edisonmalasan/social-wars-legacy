/**
 * The neighbour strip.
 *
 * The row of the players next to you: their name, their level and
 * their experience. The **model** is the client's own
 * (`packages/client/src/neighbours.ts`): the order, and who may be
 * hurried up. This is the drawing of it.
 *
 * The client shows a neighbour's **Facebook photo**, which the clone
 * does not have — the original's `graph.facebook` calls are inert here
 * — so the portrait is a placeholder and the rest of the strip is the
 * game's.
 */
import { formatNumber } from '@swl/client';
import { neighbourStrip, type Neighbour } from '@swl/client';

/** The neighbour strip's props. */
export interface NeighboursProps {
  /** The server's answer: the other players. */
  neighbours: readonly Neighbour[];
}

/**
 * The neighbour strip.
 *
 * The order is the model's — the server's — and the general is kept in
 * the strip, because the client shows him too.
 */
export function Neighbours({ neighbours }: NeighboursProps): React.JSX.Element {
  const entries = neighbourStrip(neighbours);
  return (
    <div className="swl-neighbours">
      {entries.map((entry) => (
        <div key={entry.neighbour.id} className="swl-neighbour">
          <div className="swl-neighbour-portrait" />
          <div className="swl-neighbour-name">{entry.neighbour.name}</div>
          <div className="swl-neighbour-level">level {entry.neighbour.level}</div>
          <div className="swl-neighbour-xp">XP {formatNumber(entry.neighbour.xp)}</div>
        </div>
      ))}
    </div>
  );
}
