/**
 * Magic and tech: the ten spells in the content's `magics` table.
 *
 * The specification is the client: `core/magic/MagicSpell.as` and its
 * subclasses, `core/MagicManager.as`, `GUI/SelectedMagic.as`,
 * `popups/PopupBuyMana.as`, and the three command classes. The content's
 * `magics` array is the data; there is no separate tech table.
 *
 * ## The counters
 *
 * `privateState.magics` is a map from a spell id, as a string, to the number
 * of **uses**. A missing key means "not learned"; `0` means learned and never
 * cast. Buying a spell writes `0`; casting increments the counter. The spell
 * level is derived from the counter:
 *
 * | Uses | Level |
 * |---|---|
 * | none | 0 - not learned |
 * | 0 .. 24 | 1 |
 * | 25 .. 49 | 2 |
 * | 50 or more | 3 |
 *
 * (`MagicSpell.getLevel()`, `SelectedMagic.enableKnownSpellZone()`.)
 *
 * ## The purchase quirk
 *
 * `CmdBuyMagic` charges the spell's gold or cash price and **adds** its mana
 * cost to the wallet (`commands/CmdBuyMagic.as:8-14`). The client shows the
 * same `+mana` particle after a purchase
 * (`GUI/SelectedMagic.as:200-207`), so the first cast is effectively paid for
 * by learning the spell. The clone keeps that behaviour, and both the price
 * and the mana grant come from the content, never from the client.
 *
 * The cash button stays enabled below the unlock level; only the gold button
 * is hidden (`GUI/SelectedMagic.as:39-57`). The clone keeps that too: cash may
 * unlock a spell early, gold may not.
 *
 * ## What the server does not decide
 *
 * The legacy `use_magic` command carries only the spell id, not a target
 * (`commands/CmdUseMagic.as:9-14`), so the server cannot re-simulate the
 * spell's battle effect. It owns the economy - mana, learning and the use
 * counter - and the effect remains the client's rendering of a battle the
 * server issued. That is the original protocol's own limit, not a new one.
 */

/** The resources a spell's price can be paid in: gold or cash. */
export type MagicPayment = 'g' | 'c';

/** A spell from the content's `magics` array. */
export interface MagicSpellDefinition {
  /** The spell id, 1-10 in the shipped content. */
  id: number;
  /** The display name. */
  name: string;
  /** The description shown in the wizardry popup. */
  description: string;
  /** The mana the spell costs to cast, and the mana a purchase grants. */
  mana: number;
  /** The player level that unlocks a **gold** purchase. */
  level: number;
  /** The gold price. */
  gold: number;
  /** The cash price. */
  cash: number;
  /** The affected side length for spell levels 1, 2 and 3. */
  area: number[];
  /** `0` self, `1` friendly area, `2` enemy area. */
  target: number;
  /** The asset name, without its extension. */
  imgName: string;
}

/** The price of one spell in one payment resource. */
export interface MagicPrice {
  resource: MagicPayment;
  amount: number;
}

/** The fixed mana pack the store sells. */
export interface ManaPack {
  /** The mana the pack grants. */
  amount: number;
  /** The price in each payment resource. */
  price: Record<MagicPayment, number>;
}

function numberOr(value: unknown, fallback: number): number {
  const number = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function integerOr(value: unknown, fallback: number): number {
  return Math.trunc(numberOr(value, fallback));
}

function stringOr(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

/**
 * Parse the `area` field.
 *
 * The config stores it as JSON text inside a string (`"[5,7,9]"`), because
 * the whole upstream table is stringly typed. A caller that has already
 * parsed it may pass the array.
 */
export function parseMagicArea(value: unknown): number[] {
  let parsed: unknown = value;
  if (typeof value === 'string') {
    try {
      parsed = JSON.parse(value) as unknown;
    } catch {
      return [];
    }
  }
  if (!Array.isArray(parsed)) return [];
  return parsed
    .map((entry) => integerOr(entry, 0))
    .filter((entry) => entry > 0);
}

/** One magic definition, or `null` when the entry has no usable id. */
export function magicSpellFrom(raw: unknown): MagicSpellDefinition | null {
  if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const spell = raw as Record<string, unknown>;
  const id = integerOr(spell['id'], Number.NaN);
  if (!Number.isFinite(id) || id <= 0) return null;

  return {
    id,
    name: stringOr(spell['name']),
    description: stringOr(spell['description']),
    mana: Math.max(0, integerOr(spell['mana'], 0)),
    level: Math.max(1, integerOr(spell['level'], 1)),
    gold: Math.max(0, integerOr(spell['gold'], 0)),
    cash: Math.max(0, integerOr(spell['cash'], 0)),
    area: parseMagicArea(spell['area']),
    target: integerOr(spell['target'], 0),
    imgName: stringOr(spell['img_name']),
  };
}

/**
 * The content's spells, by id.
 *
 * A duplicate id is resolved first-wins, the same way the item table is
 * de-duplicated by the content build. An entry without an id is skipped.
 */
export function magicCatalogFrom(
  raw: readonly unknown[],
): Map<number, MagicSpellDefinition> {
  const catalog = new Map<number, MagicSpellDefinition>();
  for (const entry of raw) {
    const spell = magicSpellFrom(entry);
    if (spell && !catalog.has(spell.id)) catalog.set(spell.id, spell);
  }
  return catalog;
}

/**
 * The number of times a spell has been cast, or `null` when it is not
 * learned.
 *
 * The distinction is load-bearing: an absent key and a zero mean different
 * things to the client's wizardry list. A negative value is the client's
 * own "unknown" sentinel (`MagicSpell.getLevel()` returns level 0 for it),
 * so it is treated as unlearned too.
 */
export function magicUses(magics: unknown, id: number): number | null {
  if (magics === null || typeof magics !== 'object' || Array.isArray(magics)) return null;
  const uses = (magics as Record<string, unknown>)[String(id)];
  return typeof uses === 'number' && Number.isFinite(uses) && uses >= 0 ? uses : null;
}

/** Whether a spell has been learned. */
export function isMagicLearned(magics: unknown, id: number): boolean {
  return magicUses(magics, id) !== null;
}

/**
 * A copy of the spell-use map, with only finite numeric counts.
 *
 * The copy matters: a command that is refused must not have mutated the
 * caller's world. The applier writes the copy back only after every check
 * has passed.
 */
export function magicUsesMap(magics: unknown): Record<string, number> {
  if (magics === null || typeof magics !== 'object' || Array.isArray(magics)) return {};
  const out: Record<string, number> = {};
  for (const [id, uses] of Object.entries(magics as Record<string, unknown>)) {
    if (typeof uses === 'number' && Number.isFinite(uses) && uses >= 0) out[id] = uses;
  }
  return out;
}

/** The two use counts at which a spell reaches levels 2 and 3. */
export interface SpellLevelThresholds {
  /** The number of uses that earns level 2 (`NUM_SPELL_USES_LVL2`). */
  level2: number;
  /** The number of uses that earns level 3 (`NUM_SPELL_USES_LVL3`). */
  level3: number;
}

/**
 * The spell-level thresholds the client reads from the globals.
 *
 * The third threshold is never below the second: a malformed content bundle
 * must not make level 3 unreachable or level 2 impossible to reach before it.
 */
export function spellLevelThresholds(
  globals: Record<string, unknown>,
): SpellLevelThresholds {
  const level2 = Math.max(0, integerOr(globals['NUM_SPELL_USES_LVL2'], 25));
  const level3 = Math.max(level2, integerOr(globals['NUM_SPELL_USES_LVL3'], 50));
  return { level2, level3 };
}

/**
 * The spell level a use count earns: `0` if unlearned, else `1`, `2` or `3`.
 *
 * A negative count is the client's own "unknown" sentinel
 * (`MagicSpell.getLevel()` returns 0 for it), so it is treated as unlearned.
 */
export function spellLevel(
  uses: number | null,
  globals: Record<string, unknown>,
): 0 | 1 | 2 | 3 {
  if (uses === null || !Number.isFinite(uses) || uses < 0) return 0;
  const { level2, level3 } = spellLevelThresholds(globals);
  if (uses >= level3) return 3;
  if (uses >= level2) return 2;
  return 1;
}

/**
 * The use count at which further casts stop changing anything.
 *
 * Level 3 is reached at `NUM_SPELL_USES_LVL3`; the upstream server also caps
 * the stored counter there (`upstream/socialwarriors/command.py:664-672`).
 */
export function spellUseCap(globals: Record<string, unknown>): number {
  return spellLevelThresholds(globals).level3;
}

/** The mana a player is granted for reaching a level (`MANA_REWARD_PER_LEVEL`). */
export function manaRewardPerLevel(globals: Record<string, unknown>): number {
  return Math.max(0, integerOr(globals['MANA_REWARD_PER_LEVEL'], 2));
}

/**
 * The mana pack the store sells.
 *
 * `PopupBuyMana` reads the quantity and the two prices from the globals; the
 * clone reads the same three numbers. Mana is uncapped, like the client's.
 */
export function manaPack(globals: Record<string, unknown>): ManaPack {
  return {
    amount: Math.max(0, integerOr(globals['MANA_PER_PURCHASE'], 5)),
    price: {
      c: Math.max(0, integerOr(globals['COST_MANA_CASH'], 1)),
      g: Math.max(0, integerOr(globals['COST_MANA_GOLD'], 10_000)),
    },
  };
}

/**
 * The price of a spell in one payment resource, or `null` when the spell
 * cannot be paid that way.
 */
export function magicPrice(
  spell: MagicSpellDefinition,
  payment: MagicPayment,
): MagicPrice | null {
  if (payment === 'g' && spell.gold > 0) return { resource: 'g', amount: spell.gold };
  if (payment === 'c' && spell.cash > 0) return { resource: 'c', amount: spell.cash };
  return null;
}

/**
 * Whether the payment is allowed at the player's level.
 *
 * Gold respects the spell's unlock level. Cash does not: the client leaves
 * the cash button live while hiding the gold one, which is the game's own
 * monetisation rule and is reproduced rather than corrected.
 */
export function magicLevelGate(
  spell: MagicSpellDefinition,
  playerLevel: number,
  payment: MagicPayment,
): boolean {
  if (payment === 'c') return true;
  return playerLevel >= spell.level;
}
