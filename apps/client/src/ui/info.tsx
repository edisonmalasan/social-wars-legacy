/**
 * The info panel.
 *
 * The popup the client shows for the building or the unit the player
 * selected. The **model** is the client's own (`packages/client/src/tooltips.ts`
 * and `management.ts`); the literals — "Earns:" and the hint — are the
 * client's own too.
 *
 * A building now gets a panel even when it produces nothing: the Command
 * Center, houses, walls and decorations all have a name and may have an
 * Upgrade or Finish action. Those actions only send the client's request;
 * the server still decides what happens.
 *
 * The client's defence slot shows the **attack interval**, and it does
 * so in both the tooltip and the panel, so the clone reproduces it
 * rather than "fixing" it: the client is the specification.
 */
import type { BuildingInfoView, ResourcePanel, UnitPanel } from '@swl/client';

/** The info panel's props. */
export interface InfoPanelProps {
  /** The resource building's panel, or null. */
  resource: ResourcePanel | null;
  /** The unit's panel, or null. */
  unit: UnitPanel | null;
  /** Any selected building's name and management actions, or null. */
  building?: BuildingInfoView | null;
  /** The player asked to collect the building's production. */
  onCollect?: () => void;
  /** The player asked to upgrade the building. */
  onUpgrade?: () => void;
  /** The player asked to hurry the building's construction. */
  onFinish?: () => void;
}

/**
 * The info panel.
 *
 * Nothing is drawn when nothing is selected, so the panel is the
 * client's own: it appears over the building the player clicked. The
 * heading is drawn once, whether it came from a building or a unit.
 */
export function InfoPanel({
  resource,
  unit,
  building = null,
  onCollect,
  onUpgrade,
  onFinish,
}: InfoPanelProps): React.JSX.Element | null {
  if (!resource && !unit && !building) return null;
  const name = building?.name ?? resource?.name ?? unit?.name ?? '';
  return (
    <div className="swl-info">
      <div className="swl-info-name">{name}</div>
      {resource ? (
        <>
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
      ) : null}
      {building?.upgrade || building?.finish ? (
        <div className="swl-info-actions">
          {building.upgrade ? (
            <div className="swl-info-action">
              <button
                type="button"
                className="swl-info-action-button"
                onClick={onUpgrade}
              >
                Upgrade to {building.upgrade.nextName}
              </button>
              <div className="swl-info-action-note">{building.upgrade.requirement}</div>
            </div>
          ) : null}
          {building.finish ? (
            <div className="swl-info-action">
              <button
                type="button"
                className="swl-info-action-button"
                onClick={onFinish}
              >
                Finish building
              </button>
              <div className="swl-info-action-note">
                {building.finish.remainingSeconds}s left · {building.finish.clicksToBuild} clicks
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
