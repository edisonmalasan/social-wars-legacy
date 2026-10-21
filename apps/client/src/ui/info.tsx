/**
 * The info panel.
 *
 * The popup the client shows for the building the player selected: its
 * name, the resource it produces and the amount it earns. The **model**
 * is the client's own (`packages/client/src/tooltips.ts`), and the
 * literals — "Earns:" and the hint — are the client's own too.
 */
import type { ResourcePanel } from '@swl/client';

/** The info panel's props. */
export interface InfoPanelProps {
  /** The panel's contents, or null when nothing is selected. */
  panel: ResourcePanel | null;
  /** The player asked to collect the building's production. */
  onCollect?: () => void;
}

/**
 * The info panel.
 *
 * Nothing is drawn when nothing is selected, so the panel is the
 * client's own: it appears over the building the player clicked.
 */
export function InfoPanel({ panel, onCollect }: InfoPanelProps): React.JSX.Element | null {
  if (!panel) return null;
  return (
    <div className="swl-info">
      <div className="swl-info-name">{panel.name}</div>
      <div className="swl-info-earns">
        {panel.earnsLabel} {panel.earns} {panel.resource}
      </div>
      <div className="swl-info-hint">{panel.hint}</div>
      {onCollect ? (
        <button type="button" className="swl-info-collect" onClick={onCollect}>
          Collect
        </button>
      ) : null}
    </div>
  );
}
