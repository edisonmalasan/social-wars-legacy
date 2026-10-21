/**
 * The info panel.
 *
 * The popup the client shows for the building or the unit the player
 * selected. The **model** is the client's own
 * (`packages/client/src/tooltips.ts`), and the literals — "Earns:" and
 * the hint — are the client's own too.
 *
 * The client's defence slot shows the **attack interval**, and it does
 * so in both the tooltip and the panel, so the clone reproduces it
 * rather than "fixing" it: the client is the specification.
 */
import type { ResourcePanel, UnitPanel } from '@swl/client';

/** The info panel's props. */
export interface InfoPanelProps {
  /** The resource building's panel, or null. */
  resource: ResourcePanel | null;
  /** The unit's panel, or null. */
  unit: UnitPanel | null;
  /** The player asked to collect the building's production. */
  onCollect?: () => void;
}

/**
 * The info panel.
 *
 * Nothing is drawn when nothing is selected, so the panel is the
 * client's own: it appears over the building the player clicked.
 */
export function InfoPanel({
  resource,
  unit,
  onCollect,
}: InfoPanelProps): React.JSX.Element | null {
  if (!resource && !unit) return null;
  return (
    <div className="swl-info">
      {resource ? (
        <>
          <div className="swl-info-name">{resource.name}</div>
          <div className="swl-info-earns">
            {resource.earnsLabel} {resource.earns} {resource.resource}
          </div>
          <div className="swl-info-hint">{resource.hint}</div>
          {onCollect ? (
            <button type="button" className="swl-info-collect" onClick={onCollect}>
              Collect
            </button>
          ) : null}
        </>
      ) : null}
      {unit ? (
        <>
          <div className="swl-info-name">{unit.name}</div>
          <dl className="swl-info-stats">
            <dt>Attack</dt>
            <dd>{unit.attack}</dd>
            <dt>Range</dt>
            <dd>{unit.attackRange}</dd>
            <dt>Velocity</dt>
            <dd>{unit.velocity}</dd>
            <dt>Life</dt>
            <dd>{unit.life}</dd>
            <dt>Population</dt>
            <dd>{unit.population}</dd>
            <dt>Attack interval</dt>
            <dd>{unit.attackInterval}</dd>
          </dl>
        </>
      ) : null}
    </div>
  );
}
