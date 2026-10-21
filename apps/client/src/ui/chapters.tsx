/**
 * The chapter map.
 *
 * The closest thing the game has to a minimap: the **chapters**, four of
 * them, six quests each, and the player works through them in order.
 *
 * The **model** is the client's own (`packages/client/src/chapters.ts`):
 * the slots, which are locked, which rank a quest was reached at, and
 * the chapter titles — the client's own literals. This is the drawing
 * of it.
 */
import {
  chapterMap,
  chapters as chapterList,
  type Chapter,
} from '@swl/client';

/** The chapter map's props. */
export interface ChaptersProps {
  /** The rank each quest was reached at, by the quest's index. */
  ranks: Record<number, number>;
  /** The level each quest unlocks at, by the quest's index. */
  minLevels?: Record<number, number>;
  /** How many quests the game has. */
  numQuests?: number;
}

/** One quest's slot. */
function Slot({ chapter, index }: { chapter: Chapter; index: number }): React.JSX.Element {
  const quest = chapter.quests[index];
  if (!quest) return <div className="swl-quest-slot" />;
  const locked = quest.locked;
  return (
    <div
      className={
        locked ? 'swl-quest-slot swl-quest-locked' : 'swl-quest-slot swl-quest-open'
      }
      title={locked ? `unlocks at level ${quest.levelUnlock}` : `rank ${quest.rank}`}
    >
      {locked ? '·' : quest.rank}
    </div>
  );
}

/**
 * The chapter map.
 *
 * The four chapters are the client's own, with the client's own titles,
 * and the slots are the model's: the quest the player is on is open,
 * the ones they have not reached are locked, and the ones they have
 * finished carry the rank they finished at.
 */
export function Chapters({
  ranks,
  minLevels = {},
  numQuests,
}: ChaptersProps): React.JSX.Element {
  const slots = chapterMap(ranks, { minLevels, ...(numQuests === undefined ? {} : { numQuests }) });
  const chapters = chapterList(slots);

  return (
    <div className="swl-chapters">
      {chapters.map((chapter) => (
        <div key={chapter.number} className="swl-chapter">
          <div className="swl-chapter-title">{chapter.title}</div>
          <div className="swl-chapter-quests">
            {chapter.quests.map((_, index) => (
              <Slot key={index} chapter={chapter} index={index} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
