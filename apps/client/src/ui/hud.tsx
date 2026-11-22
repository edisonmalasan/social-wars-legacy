/**
 * The HUD.
 *
 * The top bar: the player's resources, their level, their population and
 * their energy, and a popover for each that says what the number means.
 *
 * The **model** is the client's own (`packages/client/src/hud.ts`), which
 * is where the number formatting, the thresholds and the texts live, and
 * where they are tested. This is the drawing of it.
 */
import { useRef, useState } from 'react';

import {
  armyText,
  energyDisplay,
  experiencePopover,
  formatNumber,
  manaPopover,
  populationPopover,
  resourcePopover,
  xpProgress,
  type BonusPanelView,
  type HudResource,
  type HudState,
  type Popover,
} from '@swl/client';

import { InfoPopupBody } from './detailpanels.tsx';
import type { InfoPopupAnchor } from './state.ts';

/** The resources the bar shows, in the client's order. */
const RESOURCES: readonly { key: HudResource; label: string }[] = [
  { key: 'gold', label: 'Gold' },
  { key: 'wood', label: 'Wood' },
  { key: 'oil', label: 'Oil' },
  { key: 'steel', label: 'Steel' },
  { key: 'cash', label: 'Cash' },
];

/** A server-timestamp wait, in words. Presentation only. */
function wait(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return minutes > 0 ? `${minutes}m ${rest}s` : `${rest}s`;
}

/** One number on the bar, with its timed info popup. */
function Readout({
  label,
  value,
  popover,
  className,
}: {
  label: string;
  value: string;
  popover: Popover;
  className?: string;
}): React.JSX.Element {
  // The anchor is both the open flag and the popup's stable placement input:
  // it is measured on entry, so a re-render never restarts the display timer.
  const [anchor, setAnchor] = useState<InfoPopupAnchor | null>(null);
  const host = useRef<HTMLDivElement>(null);

  function show(): void {
    const rect = host.current?.getBoundingClientRect();
    if (!rect) return;
    setAnchor({ id: label, x: rect.left + rect.width / 2, y: rect.bottom });
  }

  return (
    <div
      ref={host}
      className={`swl-readout${className ? ` ${className}` : ''}`}
      onMouseEnter={show}
      onMouseLeave={() => setAnchor(null)}
      onFocus={show}
      onBlur={() => setAnchor(null)}
      tabIndex={0}
    >
      <span className="swl-readout-label">{label}</span>
      <span className="swl-readout-value">{value}</span>
      {anchor ? (
        <InfoPopupBody
          popover={popover}
          anchor={anchor}
          onExpire={() => setAnchor(null)}
        />
      ) : null}
    </div>
  );
}

/** The HUD's props. */
export interface HudProps {
  /** The player's state. */
  state: HudState;
  /** The item the player is about to place, or null. */
  placing?: string | null;
  /** The server-owned bonus cycles, read for display only. */
  bonus?: BonusPanelView | null;
  /**
   * The player asked for the daily bonus. The server decides the reward;
   * the promise, when there is one, tells the button when to unlock again.
   */
  onClaimBonus?: () => void | Promise<unknown>;
}

/**
 * The top bar.
 *
 * The numbers are the model's, and the popovers are the model's too: the
 * texts are the client's, and they are tested where they live.
 */
export function Hud({ state, placing, bonus = null, onClaimBonus }: HudProps): React.JSX.Element {
  const energy = energyDisplay(state);
  const xp = xpProgress(state);
  const [bonusBusy, setBonusBusy] = useState(false);

  /** One pending bonus request at a time; the server refuses the rest anyway. */
  function claimBonus(): void {
    if (bonusBusy) return;
    setBonusBusy(true);
    try {
      void Promise.resolve(onClaimBonus?.()).then(
        () => setBonusBusy(false),
        () => setBonusBusy(false),
      );
    } catch {
      setBonusBusy(false);
    }
  }

  return (
    <div className="swl-hud">
      <div className="swl-hud-resources">
        {placing ? (
          <span className="swl-placing">Placing: {placing} — click a tile</span>
        ) : null}
        {RESOURCES.map((resource) => (
          <Readout
            key={resource.key}
            label={resource.label}
            value={formatNumber(state[resource.key])}
            popover={resourcePopover(state, resource.key)}
            className={`swl-resource swl-resource-${resource.key}`}
          />
        ))}
      </div>
      <div className="swl-hud-player">
        <Readout
          label="Population"
          value={`${formatNumber(state.population)}/${formatNumber(state.populationMaxCurrent)}`}
          popover={populationPopover(state)}
          className="swl-population"
        />
        <Readout
          label="Level"
          value={String(state.level)}
          popover={experiencePopover(state)}
          className="swl-level"
        />
        <Readout
          label="Energy"
          value={`${formatNumber(energy.energy)}/${formatNumber(energy.max)}`}
          popover={{
            firstLine: `You have ${formatNumber(energy.energy)} of ${formatNumber(energy.max)} energy`,
            warningLine: energy.low ? 'Your energy is running low. It fills up over time.' : null,
          }}
          className="swl-energy"
        />
        <Readout
          label="Mana"
          value={formatNumber(state.mana)}
          popover={manaPopover(state)}
          className="swl-resource swl-resource-mana"
        />
        <div className="swl-xp" role="group" aria-label="Experience progress">
          <span className="swl-xp-label">XP</span>
          <span
            className="swl-xp-track"
            role="progressbar"
            aria-valuenow={Math.min(xp.current, xp.needed)}
            aria-valuemin={0}
            aria-valuemax={xp.needed}
          >
            <span className="swl-xp-fill" style={{ width: `${xp.fraction * 100}%` }} />
          </span>
          <span className="swl-xp-value">
            {formatNumber(xp.current)}/{formatNumber(xp.needed)}
          </span>
        </div>
        {bonus ? (
          <div className="swl-bonus-status" role="status">
            <span className="swl-bonus-day">Daily · day {bonus.day}</span>
            <span className="swl-bonus-when">
              {bonus.ready
                ? bonus.reset
                  ? 'Ready · new cycle'
                  : 'Ready to claim'
                : `Next in ${wait(bonus.secondsToNextDay)}`}
            </span>
            {bonus.weekly !== 'hidden' ? (
              <span className="swl-bonus-weekly">
                {bonus.weekly === 'ready'
                  ? 'Monday bonus · ready'
                  : bonus.weekly === 'collected'
                    ? 'Monday bonus · claimed'
                    : 'Monday bonus · Sunday, not ready'}
              </span>
            ) : null}
          </div>
        ) : null}
        {onClaimBonus ? (
          <button
            type="button"
            className="swl-bonus"
            disabled={bonusBusy}
            onClick={claimBonus}
          >
            Daily bonus
          </button>
        ) : null}
        <span className="swl-army">{armyText(state)}</span>
      </div>
    </div>
  );
}
