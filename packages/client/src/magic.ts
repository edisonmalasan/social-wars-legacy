/**
 * The magic screens.
 *
 * There are two:
 *
 * - the **Research LAB** (`popups/PopupWizardry.as`), which lists all ten
 *   spells six to a page, ordered by **unlock level**, and lets the player
 *   buy one, and
 * - the **spell book** (`popups/PopupMagic.as`), which lists the spells the
 *   player has learned three to a page and lets them choose one to cast.
 *
 * The server owns the outcome: `privateState.magics` is the use counter and
 * a missing key means "not learned", while `0` means "learned but never
 * cast". `privateState.mana` is the client-visible mirror of the mana in the
 * wallet. The model here only reads those facts and lays them out the way
 * the original does; buying and casting are requests.
 *
 * ## The client's rules, reproduced
 *
 * - `MagicEntry` is **learned** when the use counter exists, **available**
 *   when the player is at the spell's unlock level, and **blocked**
 *   otherwise (`GUI/MagicEntry.as:26-43`).
 * - `SelectedMagic` hides the gold button below the unlock level and
 *   **leaves the cash button live** (`GUI/SelectedMagic.as:39-57`). Cash can
 *   unlock a spell early; gold cannot.
 * - The known-spell panel fills a star per spell level, and its progress bar
 *   runs to 25 uses for level 2 and to 50 for level 3
 *   (`GUI/SelectedMagic.as:69-114`).
 * - The battle spell book contains **only learned spells**, three per page;
 *   the arrows are disabled at the ends (`popups/PopupMagic.as:124-302`).
 *   A spell the current quest disables is greyed out, and a spell with too
 *   little mana opens the mana shop instead of casting when clicked
 *   (`core/MagicManager.as:202-218`).
 *
 * The original iterates the learned map directly. JavaScript orders integer
 * keys ascending, so the battle list is id-ordered, which is the same order
 * the shipped 1-10 ids have in the client.
 */
import {
  magicCatalogFrom,
  magicLevelGate,
  magicUses,
  manaPack,
  spellLevel,
  spellLevelThresholds,
  type MagicPayment,
  type MagicSpellDefinition,
  type ManaPack,
} from '@swl/rules';

import { levelOf } from './hudstate.ts';
import type { WorldSnapshot } from './session.ts';

/** The Research LAB's page size (`PopupWizardry.NUM_SPELLS_PAGE`). */
export const MAGIC_LAB_PAGE_SIZE = 6;

/** The spell book's page size (`PopupMagic.spellNum`). */
export const MAGIC_BOOK_PAGE_SIZE = 3;

/** How a spell's row is labelled in the Research LAB. */
export type MagicStatus = 'learned' | 'available' | 'blocked';

/**
 * What the selected-spell panel shows.
 *
 * `known` is the star panel, `buy` is the two-price panel, and `locked` is
 * the same buy panel with the gold button hidden and the unlock level
 * displayed.
 */
export type MagicZone = 'known' | 'buy' | 'locked';

/** What the magic screens need to know about the player. */
export interface MagicPlayer {
  /** The player's level, which gates the gold price. */
  level: number;
  /** The player's gold. */
  gold: number;
  /** The player's cash. */
  cash: number;
  /** The client-visible mana (`privateState.mana`). */
  mana: number;
  /** The use counters (`privateState.magics`): absent means unlearned. */
  magics: unknown;
  /** Spells the current quest disables, as `MagicManager.disabledSpells`. */
  disabledSpells?: readonly number[];
}

/** The content the magic screens read. */
export interface MagicInput {
  /** The content's `magics` array. */
  spells: readonly unknown[];
  /** The content's globals. */
  globals: Record<string, unknown>;
  /** The player's state. */
  player: MagicPlayer;
}

/** One spell as the Research LAB lists it. */
export interface MagicEntryView {
  id: number;
  name: string;
  description: string;
  /** The mana cost to cast, and the mana a purchase grants. */
  mana: number;
  /** The level that unlocks a **gold** purchase. */
  unlockLevel: number;
  /** The gold price. */
  gold: number;
  /** The cash price. */
  cash: number;
  /** The image name, without its extension. */
  imgName: string;
  /** The area side length by spell level: 1, 2 and 3. */
  area: readonly number[];
  /** The area side length at the spell's current level, or null if unlearned. */
  areaForLevel: number | null;
  /** `0` self, `1` friendly area, `2` enemy area. */
  target: number;
  /** Whether the use counter exists. */
  known: boolean;
  /** Whether the player is at the unlock level. */
  available: boolean;
  /** The label the entry shows. */
  status: MagicStatus;
  /** The use count, or null when unlearned. */
  uses: number | null;
  /** The spell level: 0 when unlearned, then 1, 2 or 3. */
  level: 0 | 1 | 2 | 3;
}

/** A page of anything. */
export interface MagicPage<T> {
  /** The current page, zero-based and clamped to the available pages. */
  page: number;
  /** The number of pages; at least one, even for an empty list. */
  pageCount: number;
  /** The items on this page. */
  items: readonly T[];
  /** Whether there is a page before this one. */
  canPrev: boolean;
  /** Whether there is a page after this one. */
  canNext: boolean;
}

/** The Research LAB's state. */
export interface MagicLabPage extends MagicPage<MagicEntryView> {
  /** The player's mana. */
  mana: number;
  /** The fixed dark-matter pack. */
  pack: ManaPack;
  /** Whether each pack price can be paid. */
  canBuyMana: Record<MagicPayment, boolean>;
}

/** What the selected-spell panel shows. */
export interface MagicSelection {
  /** The spell's row, including its learned state and level. */
  entry: MagicEntryView;
  /** Which panel is visible. */
  zone: MagicZone;
  /** The filled stars: 0 when unlearned, otherwise the spell level. */
  stars: 0 | 1 | 2 | 3;
  /** Progress to the next level, from 0 to 1. */
  progress: number;
  /** The use count that earns the next level, or null at level 3. */
  nextLevelUses: number | null;
  /** Whether the gold purchase is possible now. */
  canBuyGold: boolean;
  /** Whether the cash purchase is possible now. */
  canBuyCash: boolean;
  /** Whether the spell can be cast now. */
  canCast: boolean;
  /** Whether a learned spell is short of mana. */
  needsMana: boolean;
  /** The mana a purchase grants; it is the spell's own cost. */
  manaGrant: number;
}

/** One learned spell in the battle spell book. */
export interface BattleSpell {
  id: number;
  name: string;
  imgName: string;
  /** The mana cost to cast. */
  mana: number;
  /** The area side length by spell level. */
  area: readonly number[];
  /** The area side length at the spell's current level. */
  areaForLevel: number;
  /** `0` self, `1` friendly area, `2` enemy area. */
  target: number;
  /** The use count, capped where the server caps it. */
  uses: number;
  /** The spell level, 1 to 3. */
  level: 1 | 2 | 3;
  /** Whether the current quest allows the spell to be chosen. */
  enabled: boolean;
  /** Whether the player has enough mana to cast it now. */
  castable: boolean;
}

/** The battle spell book's state. */
export interface MagicBookPage extends MagicPage<BattleSpell> {
  /** The player's mana. */
  mana: number;
}

function numberOr(value: unknown, fallback: number): number {
  const number = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(number) ? number : fallback;
}

/** A finite, non-negative amount of a resource. */
function amountOr(value: unknown): number {
  return Math.max(0, numberOr(value, 0));
}

/**
 * The player's magic state, read out of the server's snapshot.
 *
 * The client displays `privateState.mana`, not the raw wallet, so that is the
 * number this model uses; a snapshot without the mirror falls back to the
 * wallet's `m`.
 */
export function magicPlayerFromWorld(
  world: WorldSnapshot,
  disabledSpells: readonly number[] = [],
): MagicPlayer {
  const privateState = world.privateState ?? {};
  const storedMana = Number(privateState['mana']);
  return {
    level: levelOf(world),
    gold: amountOr(world.resources['g']),
    cash: amountOr(world.resources['c']),
    mana: Number.isFinite(storedMana)
      ? Math.max(0, storedMana)
      : amountOr(world.resources['m']),
    magics: privateState['magics'] ?? {},
    disabledSpells: [...disabledSpells],
  };
}

/** The magic model's input, read out of a server snapshot and the content. */
export function magicInputFromWorld(
  world: WorldSnapshot,
  spells: readonly unknown[],
  globals: Record<string, unknown>,
  disabledSpells: readonly number[] = [],
): MagicInput {
  return {
    spells,
    globals,
    player: magicPlayerFromWorld(world, disabledSpells),
  };
}

function entryOf(input: MagicInput, spell: MagicSpellDefinition): MagicEntryView {
  const uses = magicUses(input.player.magics, spell.id);
  const known = uses !== null;
  const available = input.player.level >= spell.level;
  const level = spellLevel(uses, input.globals);
  return {
    id: spell.id,
    name: spell.name,
    description: spell.description,
    mana: spell.mana,
    unlockLevel: spell.level,
    gold: spell.gold,
    cash: spell.cash,
    imgName: spell.imgName,
    area: spell.area,
    areaForLevel: level > 0 ? (spell.area[level - 1] ?? null) : null,
    target: spell.target,
    known,
    available,
    status: known ? 'learned' : available ? 'available' : 'blocked',
    uses,
    level,
  };
}

/**
 * Every spell, in the Research LAB's order.
 *
 * The client sorts by unlock level and does not break ties
 * (`PopupWizardry.sortMagicEntries`), so the content's order is kept for
 * spells that unlock at the same level.
 */
export function magicEntries(input: MagicInput): MagicEntryView[] {
  return [...magicCatalogFrom(input.spells).values()]
    .map((spell) => entryOf(input, spell))
    .sort((a, b) => a.unlockLevel - b.unlockLevel);
}

/**
 * Split a list into pages.
 *
 * A page that is out of range is clamped rather than allowed to show an
 * empty page; the arrows are driven by `canPrev` and `canNext`.
 */
export function paginate<T>(
  items: readonly T[],
  page: number,
  pageSize: number,
): MagicPage<T> {
  const size = Math.max(1, Math.trunc(pageSize));
  const pageCount = Math.max(1, Math.ceil(items.length / size));
  const requested = Number.isFinite(page) ? Math.trunc(page) : 0;
  const current = Math.min(Math.max(0, requested), pageCount - 1);
  const start = current * size;
  return {
    page: current,
    pageCount,
    items: items.slice(start, start + size),
    canPrev: current > 0,
    canNext: current + 1 < pageCount,
  };
}

/** The Research LAB, one page at a time. */
export function magicLab(input: MagicInput, page = 0): MagicLabPage {
  const paged = paginate(magicEntries(input), page, MAGIC_LAB_PAGE_SIZE);
  const pack = manaPack(input.globals);
  return {
    ...paged,
    mana: input.player.mana,
    pack,
    canBuyMana: {
      c: pack.price.c > 0 && input.player.cash >= pack.price.c,
      g: pack.price.g > 0 && input.player.gold >= pack.price.g,
    },
  };
}

/**
 * The progress bar's fill for one spell.
 *
 * The client fills it to the level-2 threshold, then from level 2 to level
 * 3, and leaves it full at level 3 (`GUI/SelectedMagic.as:89-103`). A spell
 * that has never been cast shows an empty bar even though its first star is
 * already filled.
 */
export function magicProgress(
  uses: number | null,
  globals: Record<string, unknown>,
): number {
  if (uses === null || uses <= 0) return 0;
  const { level2, level3 } = spellLevelThresholds(globals);
  if (uses < level2) {
    return level2 > 0 ? Math.min(uses / level2, 1) : 1;
  }
  if (uses < level3) {
    return level3 > level2
      ? Math.min((uses - level2) / (level3 - level2), 1)
      : 1;
  }
  return 1;
}

/**
 * The selected spell's panel.
 *
 * `null` when the id is not in the content, which is the only case the
 * client cannot show at all.
 */
export function selectedMagic(
  input: MagicInput,
  spellId: number,
): MagicSelection | null {
  const spell = magicCatalogFrom(input.spells).get(spellId);
  if (!spell) return null;

  const entry = entryOf(input, spell);
  const zone: MagicZone = entry.known
    ? 'known'
    : entry.available
      ? 'buy'
      : 'locked';
  const uses = entry.uses;
  const thresholds = spellLevelThresholds(input.globals);
  const nextLevelUses =
    entry.level === 1
      ? thresholds.level2
      : entry.level === 2
        ? thresholds.level3
        : null;

  const canBuyGold =
    !entry.known &&
    magicLevelGate(spell, input.player.level, 'g') &&
    spell.gold > 0 &&
    input.player.gold >= spell.gold;
  const canBuyCash =
    !entry.known &&
    magicLevelGate(spell, input.player.level, 'c') &&
    spell.cash > 0 &&
    input.player.cash >= spell.cash;
  const canCast = entry.known && input.player.mana >= spell.mana;

  return {
    entry,
    zone,
    stars: entry.level,
    progress: magicProgress(uses, input.globals),
    nextLevelUses,
    canBuyGold,
    canBuyCash,
    canCast,
    needsMana: entry.known && !canCast,
    manaGrant: spell.mana,
  };
}

/**
 * The battle spell book, one page at a time.
 *
 * Only learned spells are listed. The original's `SpellButton` stays
 * enabled when mana is short and opens the mana shop on a click, so
 * `castable` is separate from `enabled`: `enabled` is the quest's veto and
 * `castable` is the mana check.
 */
export function magicBook(input: MagicInput, page = 0): MagicBookPage {
  const disabled = new Set(input.player.disabledSpells ?? []);
  const learned = [...magicCatalogFrom(input.spells).values()]
    .filter((spell) => magicUses(input.player.magics, spell.id) !== null)
    .sort((a, b) => a.id - b.id)
    .map((spell): BattleSpell => {
      const uses = magicUses(input.player.magics, spell.id) ?? 0;
      const level = spellLevel(uses, input.globals);
      const enabled = !disabled.has(spell.id);
      return {
        id: spell.id,
        name: spell.name,
        imgName: spell.imgName,
        mana: spell.mana,
        area: spell.area,
        areaForLevel: spell.area[level - 1] ?? 0,
        target: spell.target,
        uses,
        level: level === 0 ? 1 : level,
        enabled,
        castable: enabled && input.player.mana >= spell.mana,
      };
    });

  return {
    ...paginate(learned, page, MAGIC_BOOK_PAGE_SIZE),
    mana: input.player.mana,
  };
}
