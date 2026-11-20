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

import type { ProductionPanelView } from './state.ts';

/** The shared dialog's id for the collection-period selector. */
export const PRODUCTION_DIALOG_ID = 'production';

/** A broken-down server-timestamp countdown, for display only. */
function countdown(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = seconds % 60;
  return hours > 0
    ? `${hours}h ${minutes}m ${rest}s`
    : `${minutes}m ${rest}s`;
}

/** A period's wait, in the game's own units. */
function wait(minutes: number): string {
  return minutes % 60 === 0 ? `${minutes / 60} h` : `${minutes} min`;
}

/** The collection-period selector hosted by the shared dialog. */
export interface ProductionSelectorProps {
  /** The server-and-content reading the buttons draw. */
  readonly view: ProductionPanelView;
  /** The player picked one of the content's periods; the server decides. */
  readonly onActivate: (period: number) => void;
}

/**
 * The four collection periods and the active cycle's countdown.
 *
 * Every duration and multiplier comes from the content through
 * `ProductionPanelView`, and the countdown from the server's timestamp. The
 * buttons only send the `activate` request; they never start a cycle locally
 * and never promise a payout — the server's answer is drawn as feedback.
 */
export function ProductionSelector({
  view,
  onActivate,
}: ProductionSelectorProps): React.JSX.Element {
  return (
    <div className="swl-production">
      <div className="swl-production-head">
        {view.name} · {view.resource.toUpperCase()}
      </div>
      <div className="swl-production-cycle" role="status">
        {view.due
          ? 'Ready to collect'
          : `Ready in ${countdown(view.secondsRemaining)}`}
      </div>
      <div className="swl-production-options">
        {view.options.map((option) => (
          <button
            key={option.period}
            type="button"
            className={
              option.active
                ? 'swl-production-option swl-production-option-active'
                : 'swl-production-option'
            }
            aria-pressed={option.active}
            onClick={() => onActivate(option.period)}
          >
            <span className="swl-production-wait">{wait(option.minutes)}</span>
            <span className="swl-production-mult">×{option.multiplier}</span>
            <span className="swl-production-amount">
              +{option.amount} {view.resource}
            </span>
          </button>
        ))}
      </div>
      <p className="swl-production-note">
        The server starts the countdown when a period is chosen.
      </p>
    </div>
  );
}

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
  /** The selected building's production cycle, when it can choose one. */
  production?: ProductionPanelView | null;
  /** The player asked to open the collection-period selector. */
  onOpenProduction?: () => void;
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
  production = null,
  onOpenProduction,
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
          {production ? (
            <div className="swl-info-production">
              {production.due
                ? 'Ready to collect'
                : `Next in ${countdown(production.secondsRemaining)}`}
            </div>
          ) : null}
          {onCollect ? (
            <button type="button" className="swl-info-collect" onClick={onCollect}>
              Collect
            </button>
          ) : null}
          {production && onOpenProduction ? (
            <button
              type="button"
              className="swl-info-period-button"
              onClick={onOpenProduction}
            >
              Choose collection period
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
