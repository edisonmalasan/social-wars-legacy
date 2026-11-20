/**
 * The chapter map.
 *
 * The closest thing the game has to a minimap: the **chapters**, four of
 * them, six quests each, and the player works through them in order.
 *
 * The **model** is the client's own (`packages/client/src/chapters.ts`):
 * the slots, which are locked, which rank a quest was reached at, and
 * the chapter titles — the client's own literals. This is the drawing
 * of it. A slot the server has opened is now a **button**: clicking it
 * opens that quest's briefing (or resumes its active panel), rather than
 * leaving the player with no way into the quest workflow.
 */
import {
  chapterMap,
  chapters as chapterList,
  type Chapter,
  type QuestChoice,
} from '@swl/client';

/** The chapter map's props. */
export interface ChaptersProps {
  /** The rank each quest was reached at, by the quest's index. */
  ranks: Record<number, number>;
  /** The level each quest unlocks at, by the quest's index. */
  minLevels?: Record<number, number>;
  /** How many quests the game has. */
  numQuests?: number;
  /** The pickable quest, by the slot's index. */
  choices?: readonly QuestChoice[];
  /** The player picked an opened slot. */
  onQuestPick?: (choice: QuestChoice) => void;
}

/** One quest's slot. */
function Slot({
  chapter,
  index,
  choice,
  onQuestPick,
}: {
  chapter: Chapter;
  index: number;
  choice: QuestChoice | null;
  onQuestPick?: (choice: QuestChoice) => void;
}): React.JSX.Element {
  const quest = chapter.quests[index];
  if (!quest) return <div className="swl-quest-slot" />;
  const locked = quest.locked;
  const pickable = choice && !choice.locked && onQuestPick ? choice : null;
  const style = [
    'swl-quest-slot',
    locked ? 'swl-quest-locked' : 'swl-quest-open',
    choice?.active ? 'swl-quest-active' : '',
  ]
    .filter(Boolean)
    .join(' ');
  const title = choice?.active
    ? `Resume ${choice.title}`
    : locked
      ? `unlocks at level ${quest.levelUnlock}`
      : `rank ${quest.rank}`;
  const content = locked ? '·' : quest.rank;
  if (pickable) {
    return (
      <button
        type="button"
        className={style}
        title={title}
        aria-label={title}
        onClick={() => onQuestPick!(pickable)}
      >
        {content}
      </button>
    );
  }
  return (
    <div className={style} title={title}>
      {content}
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
  choices = [],
  onQuestPick,
}: ChaptersProps): React.JSX.Element {
  const slots = chapterMap(ranks, { minLevels, ...(numQuests === undefined ? {} : { numQuests }) });
  const chapters = chapterList(slots);
  const byIndex = new Map(choices.map((choice) => [choice.index, choice]));

  return (
    <div className="swl-chapters">
      {chapters.map((chapter) => (
        <div key={chapter.number} className="swl-chapter">
          <div className="swl-chapter-title">{chapter.title}</div>
          <div className="swl-chapter-quests">
            {chapter.quests.map((_, index) => (
              <Slot
                key={index}
                chapter={chapter}
                index={index}
                choice={byIndex.get(index + 1) ?? null}
                onQuestPick={onQuestPick}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
