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
import { useState } from 'react';

import {
  armyText,
  energyDisplay,
  experiencePopover,
  formatNumber,
  populationPopover,
  resourcePopover,
  type HudResource,
  type HudState,
  type Popover,
} from '@swl/client';

/** The resources the bar shows, in the client's order. */
const RESOURCES: readonly { key: HudResource; label: string }[] = [
  { key: 'gold', label: 'Gold' },
  { key: 'wood', label: 'Wood' },
  { key: 'oil', label: 'Oil' },
  { key: 'steel', label: 'Steel' },
  { key: 'cash', label: 'Cash' },
];

/** A popover, in the markup. */
function PopoverBox({ popover }: { popover: Popover }): React.JSX.Element {
  return (
    <div className="swl-popover" role="tooltip">
      <p className="swl-popover-first">{popover.firstLine}</p>
      {popover.warningLine ? (
        <p className="swl-popover-warning">{popover.warningLine}</p>
      ) : null}
    </div>
  );
}

/** One number on the bar, with its popover. */
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
  const [open, setOpen] = useState(false);
  return (
    <div
      className={`swl-readout${className ? ` ${className}` : ''}`}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      tabIndex={0}
    >
      <span className="swl-readout-label">{label}</span>
      <span className="swl-readout-value">{value}</span>
      {open ? <PopoverBox popover={popover} /> : null}
    </div>
  );
}

/** The HUD's props. */
export interface HudProps {
  /** The player's state. */
  state: HudState;
}

/**
 * The top bar.
 *
 * The numbers are the model's, and the popovers are the model's too: the
 * texts are the client's, and they are tested where they live.
 */
export function Hud({ state }: HudProps): React.JSX.Element {
  const energy = energyDisplay(state);
  return (
    <div className="swl-hud">
      <div className="swl-hud-resources">
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
        <span className="swl-army">{armyText(state)}</span>
      </div>
    </div>
  );
}
