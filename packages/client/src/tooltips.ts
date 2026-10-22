import { levelForXp, xpForLevel, type XpLevelRow } from '@swl/rules';

/**
 * The tooltips.
 *
 * The client has five tooltip surfaces:
 *
 * - the **HUD's resource tooltips**, which are four fixed sentences about
 *   the resources (`core/GuiManager.as:2453-2490`);
 * - the **info panel**, which is built from the item's own statistics. It
 *   is the "extended portrait", and each kind of item has its own
 *   delegate to fill it in (`core/isoengine/delegates/`);
 * - the **icon panel's dictionary**, the sentences on the strip of promo
 *   and bonus buttons (`GUI/IconPanel.as`, `GUI/GuiManager.as:801-890`);
 * - the **special units' attack tooltips**, the longer sentence a hero's
 *   attack button shows on a hover (`GUI/PortraitSpecialAttack.as:80-101`);
 * - the **marketplace's unit tip**, the card an auction listing shows on
 *   a hover (`popups/marketplace/MarketplaceUnitInfoTip.as`).
 *
 * ## The client's defence slot
 *
 * Both the unit tooltip and the unit's extended portrait put the
 * **attack interval** in the slot named `mcDefense`:
 *
 * ```as3
 * // GUI/UnitTooltip.as:44
 * this.tt.mcDefense.txDefense = _loc3_.attack_interval;
 *
 * // core/isoengine/delegates/AbstractUnitDelegate.as:160
 * TextFieldUtil.setHTML(param1.extendedPortrait.mcDefense.txDefense, _loc2_.attack_interval);
 * ```
 *
 * That is the client's behaviour, in both places, so it is not a
 * slip in one of them — the client shows the attack rate there. The clone
 * reproduces it rather than "fixing" it, because the client is the
 * specification.
 *
 * ## The attack the panel shows
 *
 * The panel does not show the item's base attack. It shows the unit's
 * **effective** attack against what it is aimed at, the base multiplied
 * by the match-up bonus:
 *
 * ```as3
 * var _loc3_:String = String(this.self.uiAttack * _loc2_.best_against_mult);
 * ```
 *
 * and, when the unit has an XP level, the level's extra attack is added
 * to it as text.
 */

/**
 * The HUD's resource tooltips.
 *
 * The client's own literals. The four the HUD shows are food, wood,
 * stone and gold; the other resources are shown with their own icons and
 * no sentence.
 */
export const RESOURCE_TOOLTIPS = {
  energy: 'Food: Used to feed units',
  wood: 'Wood: Used to build basic constructions',
  steel: 'Stone: Used to build defensive constructions',
  gold: 'Gold: Used to pay military units',
} as const;

/** The resource whose tooltip is shown. */
export type TooltipResource = keyof typeof RESOURCE_TOOLTIPS;

/** The tooltip of a resource in the HUD, or null when it has none. */
export function resourceTooltip(resource: string): string | null {
  return (RESOURCE_TOOLTIPS as Record<string, string>)[resource] ?? null;
}

/**
 * The literal the resource building's info panel shows above the amount.
 *
 * `core/isoengine/delegates/ResourceDelegate.as:50`.
 */
export const EARNS_LABEL = 'Earns:';

/**
 * The literal the resource building's info panel shows as its hint.
 *
 * `core/isoengine/delegates/ResourceDelegate.as:51`.
 */
export const RESOURCE_HINT =
  'Select a peasant and click this resource to harvest it.';

/** The content of a resource building. */
export interface ResourceItem {
  name: string;
  /** Which resource it produces: `w`, `o`, `s`, `c` or `g`. */
  collect_type: string;
  /** The base amount it produces per cycle. */
  collect: number;
}

/** The info panel of a resource building. */
export interface ResourcePanel {
  kind: 'resource';
  /** The building's name. */
  name: string;
  /** Which resource it produces. */
  resource: string;
  /** The base amount it produces per cycle. */
  earns: number;
  /** The literal above the amount. */
  earnsLabel: string;
  /** The hint under the panel. */
  hint: string;
}

/** Build a resource building's info panel. */
export function resourcePanel(item: ResourceItem): ResourcePanel {
  return {
    kind: 'resource',
    name: item.name,
    resource: item.collect_type,
    earns: item.collect,
    earnsLabel: EARNS_LABEL,
    hint: RESOURCE_HINT,
  };
}

/** The content of a unit. */
export interface UnitItem {
  name: string;
  /** Its base attack. */
  attack: number;
  /** Its life. */
  life: number;
  /** How long it waits between attacks, in frames at 30 fps. */
  attack_interval: number;
  /** How far it can reach. */
  attack_range: number;
  /** How fast it moves. */
  velocity: number;
  /** How much population it takes. */
  population: number;
  /** The bonus it gets against what it is weak against. */
  best_against_mult?: number;
}

/** The info panel of a unit. */
export interface UnitPanel {
  kind: 'unit';
  /** The unit's name. */
  name: string;
  /** The attack the panel shows: the effective attack. */
  attack: number;
  /** The attack range. */
  attackRange: number;
  /** The attack interval, which the client shows in the defence slot. */
  attackInterval: number;
  /** The velocity. */
  velocity: number;
  /** The life, which the tooltip shows and the panel's bar fills. */
  life: number;
  /** The population it takes. */
  population: number;
  /** The unit's special description, when it has one. */
  specialDescription?: string;
}

/**
 * Build a unit's info panel.
 *
 * @param item the unit's content
 * @param effectiveAttack the unit's attack against what it is aimed at,
 *   which the server computes. When it is not given, the unit's own base
 *   attack is shown.
 * @param specialDescription the unit's special description, when it has one
 */
export function unitPanel(
  item: UnitItem,
  effectiveAttack?: number,
  specialDescription?: string,
): UnitPanel {
  return {
    kind: 'unit',
    name: item.name,
    attack: effectiveAttack ?? item.attack,
    attackRange: item.attack_range,
    attackInterval: item.attack_interval,
    velocity: item.velocity,
    life: item.life,
    population: item.population,
    ...(specialDescription ? { specialDescription } : {}),
  };
}

/**
 * The tooltip of a unit, which the client shows on a hover.
 *
 * It is the same panel without the portrait, plus the life and the
 * population.
 */
export interface UnitTooltip {
  name: string;
  life: number;
  attack: number;
  /** The attack interval, in the client's defence slot. */
  attackInterval: number;
  velocity: number;
  attackRange: number;
  population: number;
  /** The special description, when the unit has one. */
  specialDescription?: string;
}

/** Build a unit's tooltip. */
export function unitTooltip(
  item: UnitItem,
  effectiveAttack?: number,
  specialDescription?: string,
): UnitTooltip {
  return {
    name: item.name,
    life: item.life,
    attack: effectiveAttack ?? item.attack,
    attackInterval: item.attack_interval,
    velocity: item.velocity,
    attackRange: item.attack_range,
    population: item.population,
    ...(specialDescription ? { specialDescription } : {}),
  };
}

/**
 * The attack the panel shows.
 *
 * The client's own rule: the unit's effective attack against what it is
 * aimed at, the base multiplied by the match-up bonus, and the XP level's
 * extra attack added to it as text.
 *
 * ```as3
 * var _loc3_:String = String(this.self.uiAttack * _loc2_.best_against_mult);
 * if (this.self.buildingReference.unitXPLevel.extraAttack) {
 *    _loc3_ += "+" + this.self.buildingReference.unitXPLevel.extraAttack;
 * }
 * ```
 */
export function panelAttack(
  effectiveAttack: number,
  bestAgainstMult: number,
  extraAttack = 0,
): string {
  const value = effectiveAttack * bestAgainstMult;
  return extraAttack > 0 ? `${value}+${extraAttack}` : String(value);
}

/**
 * Fill the client's `#0#`, `#1#` … parameter tokens.
 *
 * `Language.getLiteral` splits the sentence on `#` and puts the array's
 * value in every odd slot:
 *
 * ```as3
 * _loc4_ = _loc3_.split(TOKEN_PARAMETER); // "#"
 * while(_loc7_ < _loc5_) {
 *    _loc6_ = parseInt(_loc4_[_loc7_ * 2 + 1]);
 *    _loc4_[_loc7_ * 2 + 1] = param2[_loc6_];
 * }
 * _loc3_ = _loc4_.join("");
 * ```
 *
 * `Array.join` turns a missing value into the empty string, so the clone
 * does the same (`core/Language.as:105-138`).
 */
export function literalText(
  literal: string,
  params: readonly (string | number)[] = [],
): string {
  const parts = literal.split('#');
  const pairs = Math.floor((parts.length - 1) / 2);
  for (let pair = 0; pair < pairs; pair++) {
    const at = pair * 2 + 1;
    const value = params[Number.parseInt(parts[at]!, 10)];
    parts[at] = value === undefined || value === null ? '' : String(value);
  }
  return parts.join('');
}

/**
 * The icon panel's dictionary.
 *
 * `GUI/IconPanel.as:84-94` stores one sentence per icon; `GUI/GuiManager.as`
 * passes them at the call sites. The offer, video and Facebook promo buttons
 * are added without a sentence, so they have none.
 */
export const ICON_PANEL_TOOLTIPS = {
  dailyBonus: 'Get your daily Bonus!',
  mondayBonus: 'Get your Monday Bonus!',
  dragonCityMobile: 'Dragon City Mobile',
  gameCrossPromotion: 'Play #0#!',
} as const;

/** The buttons the icon panel has a sentence for. */
export type IconPanelButton = keyof typeof ICON_PANEL_TOOLTIPS;

/**
 * The tooltip of an icon panel button, or null when it has none.
 *
 * `params` fills the sentence's `#0#` tokens, the way the client passes the
 * cross-promotion's game name: `Play #0#!` becomes `Play Dragon City!`.
 */
export function iconPanelTooltip(
  button: string,
  params: readonly (string | number)[] = [],
): string | null {
  const literal = (ICON_PANEL_TOOLTIPS as Record<string, string>)[button];
  return literal === undefined ? null : literalText(literal, params);
}

/**
 * One attack record from `re/data/unit-behaviour.json`.
 *
 * The extractor writes the display name, the button icon, the "cannot use"
 * message and the hover sentence. A factory-built attack's cannot-message is
 * often computed at runtime, so it may be null.
 */
export interface SpecialAttackRecord {
  kind: string;
  name: string | null;
  icon: string | null;
  cantMessage?: string | null;
  tooltip?: string | null;
}

/**
 * The sentence a special attack's portrait shows on a hover, or null.
 *
 * `GUI/PortraitSpecialAttack.as:80-90` opens the pop-over only when the
 * attack's tooltip is not the empty string.
 *
 * `SpecialUnitAttackCreator` has no `withTooltip`, and its `create()` calls
 * the constructor with nine arguments, so a factory-built attack never has
 * one (`core/generalAttacks/SpecialUnitAttackCreator.as:26-83`).
 */
export function specialAttackTooltip(
  attack: Pick<SpecialAttackRecord, 'tooltip'>,
  params: readonly (string | number)[] = [],
): string | null {
  const tooltip = attack.tooltip;
  return tooltip ? literalText(tooltip, params) : null;
}

/**
 * The marketplace's unit tip.
 *
 * `popups/marketplace/MarketplaceUnitInfoTip.as:10-21` shows the unit's
 * name, total life, total attack, range, population, velocity and attack
 * interval. The interval is in the defence slot here too.
 */
export interface MarketplaceUnitTip {
  name: string;
  /** The base life plus the listing's XP bonus. */
  life: number;
  /** The base attack plus the listing's XP bonus. */
  attack: number;
  attackRange: number;
  population: number;
  velocity: number;
  /** The attack interval, in the client's defence slot. */
  attackInterval: number;
}

/**
 * Build the marketplace's unit tip for a listing at `tier`.
 *
 * The client shows **one level low**. It seeds `UnitXPLevelInfo` with the XP
 * needed for the listing's own tier, and the level loop breaks on `<=`, so a
 * tier-N listing is evaluated as level N-1
 * (`data/MarketplaceUnitInfo.as:86`, `core/UnitXPLevelInfo.as:57-83`).
 *
 * The extra life is accumulated one level at a time in a `uint`, so each
 * level's percentage is truncated before the next is added. That is not the
 * same as truncating the summed percentage
 * (`core/UnitXPLevelInfo.as:77`).
 */
export function marketplaceUnitTip(
  item: UnitItem,
  tier: number,
  table: readonly XpLevelRow[],
): MarketplaceUnitTip {
  const top = Math.max(0, Math.min(table.length - 1, Math.trunc(tier)));
  const level = levelForXp(table, item.life, xpForLevel(table, item.life, top));

  let extraAttack = 0;
  let extraLife = 0;
  for (let candidate = 1; candidate <= level; candidate++) {
    const row = table[candidate]!;
    extraAttack += row.flatAttack;
    extraLife = Math.trunc(extraLife + item.life * (row.lifePercent / 100));
  }

  return {
    name: item.name,
    life: Math.trunc(item.life) + extraLife,
    attack: Math.trunc(item.attack) + extraAttack,
    attackRange: item.attack_range,
    population: item.population,
    velocity: item.velocity,
    attackInterval: item.attack_interval,
  };
}
