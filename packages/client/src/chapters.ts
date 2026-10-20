/**
 * The chapter map.
 *
 * The goal panel's map is the game's **chapters**: four of them, six
 * quests each, and the player works through them in order. It is the
 * closest thing the game has to a minimap — there is no minimap.
 *
 * ## Which quests are available
 *
 * The client's own rule (`popups/PopupQuestsMap.as:setQuestsInfo`):
 *
 * ```as3
 * for (var index = 1; index <= maxQuests; index++) {
 *    if (Base.Player.questsRank[index] != undefined) {
 *       // the quest has been ranked: it is available, at that rank
 *    } else if (index == nextIndex && index <= Quest.numQuests) {
 *       // the first unranked quest: it is available, at rank 0
 *    } else {
 *       // everything else is locked
 *    }
 * }
 * ```
 *
 * So a quest's **rank** is what the player has reached it at, the first
 * unranked quest is the one in progress, and the rest are locked. The
 * ranks are the server's: the client asks for them with
 * `admin_set_quest_rank` after every quest, and the server keeps them.
 */

/** How many quests can be ranked. The client's own `maxQuests`. */
export const MAX_QUESTS = 22;

/** How many chapters the map has. The client's own `_numberMaps`. */
export const CHAPTERS = 4;

/** How many quests each chapter holds. The client's own `_numberQuestsPerMap`. */
export const QUESTS_PER_CHAPTER = 6;

/** One quest's slot on the map. */
export interface QuestSlot {
  /** The quest's index, 1-based. */
  index: number;
  /** The rank the player reached it at. Zero when it has not been ranked. */
  rank: number;
  /** Whether the quest is locked. */
  locked: boolean;
  /** The level the quest unlocks at. Zero when it unlocks at once. */
  levelUnlock: number;
}

/** One chapter of the map. */
export interface Chapter {
  /** The chapter's number, 1-based. */
  number: number;
  /** The chapter's title. */
  title: string;
  /** The building whose portrait the chapter shows, or null. */
  thumb: number | null;
  /** The chapter's quests, in order. */
  quests: QuestSlot[];
}

/**
 * The chapter titles.
 *
 * The client's own literals (`PopupQuestsMap.mapTitles`). The fourth
 * chapter shares the third's title, which is the client's own wording.
 */
export const CHAPTER_TITLES: readonly string[] = [
  'SMALL HARBOUR MISSIONS',
  'HARBOUR MISSIONS',
  'SPACE MISSIONS',
  'SPACE MISSIONS',
];

/** The buildings the chapters' portraits come from. */
export const CHAPTER_THUMBS: readonly (number | null)[] = [
  // The client's own: the small harbour, the harbour, and then nothing.
  null,
  null,
  null,
  null,
];

/** What the chapter map needs. */
export interface ChapterMapOptions {
  /** How many quests the game has. The client's `Quest.numQuests`. */
  numQuests?: number;
  /** The level each quest unlocks at, by the quest's index. */
  minLevels?: Record<number, number>;
}

/**
 * The map's slots.
 *
 * @param ranks the player's quest ranks, by the quest's index
 */
export function chapterMap(
  ranks: Readonly<Record<number, number>> = {},
  options: ChapterMapOptions = {},
): QuestSlot[] {
  const numQuests = options.numQuests ?? MAX_QUESTS;
  const minLevels = options.minLevels ?? {};
  const slots: QuestSlot[] = [];

  // The first quest that has not been ranked: the one in progress.
  let next = 1;

  for (let index = 1; index <= MAX_QUESTS; index++) {
    const rank = ranks[index];
    const levelUnlock = minLevels[index] ?? 0;

    if (rank !== undefined) {
      // The quest has been ranked: it is available, at that rank.
      slots.push({ index, rank: Number(rank), locked: false, levelUnlock });
      next = index + 1;
    } else if (index === next && index <= numQuests) {
      // The first unranked quest: it is the one in progress.
      slots.push({ index, rank: 0, locked: false, levelUnlock });
    } else {
      // Everything else is locked.
      slots.push({ index, rank: 0, locked: true, levelUnlock });
    }
  }

  // The slots the quests do not fill.
  for (let index = MAX_QUESTS + 1; index <= CHAPTERS * QUESTS_PER_CHAPTER; index++) {
    slots.push({ index, rank: 0, locked: true, levelUnlock: 0 });
  }

  return slots;
}

/**
 * The chapters.
 *
 * The map's slots, grouped into the chapters, in order.
 */
export function chapters(
  slots: readonly QuestSlot[],
  titles: readonly string[] = CHAPTER_TITLES,
  thumbs: readonly (number | null)[] = CHAPTER_THUMBS,
): Chapter[] {
  const out: Chapter[] = [];
  for (let number = 1; number <= CHAPTERS; number++) {
    const from = (number - 1) * QUESTS_PER_CHAPTER;
    out.push({
      number,
      title: titles[number - 1] ?? '',
      thumb: thumbs[number - 1] ?? null,
      quests: slots.slice(from, from + QUESTS_PER_CHAPTER),
    });
  }
  return out;
}
