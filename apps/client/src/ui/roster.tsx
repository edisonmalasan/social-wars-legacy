/**
 * The army roster, team-thumbnail and unit-XP panel.
 *
 * This is a **body hosted by the one shared dialog** in `dialog.tsx`; it never
 * creates a second modal. Everything it draws is a reading of the server's
 * save and the content, bridged by `state.ts`: the roster is `armyView`, the
 * thumbnails echo the team the server bound to the active quest, and the XP
 * card uses the rules' level and the client's own literals.
 *
 * The team counts and the inspected row are the player's own UI gestures, held
 * only for this panel. They never field a unit: the only game gesture here is
 * "Use this team", which hands the candidate team to the host, and the host
 * sends it as a request. The server still decides which units it accepts.
 */
import { useSyncExternalStore, useState } from 'react';

import { chooseArmyCount, initialArmySelection } from '@swl/client';
import type { Army } from '@swl/rules';

import type { RosterPanelView, RosterUnitView, UnitXpView } from './state.ts';

/** The callbacks the host publishes for this family. */
export interface RosterHost {
  /** Open the roster in the one shared dialog. */
  readonly open: (() => void) | null;
  /** Ask the server to use the composed team, with the host's chosen request. */
  readonly submitTeam: ((team: Army) => void) | null;
}

const CLOSED_HOST: RosterHost = { open: null, submitTeam: null };

let host: RosterHost = CLOSED_HOST;
const listeners = new Set<() => void>();

/** Publish (or clear) the host's gestures for this panel. */
export function setRosterHost(patch: Partial<RosterHost>): void {
  host = { ...host, ...patch };
  for (const listener of listeners) listener();
}

/** The current UI-only roster host. */
export function rosterHost(): RosterHost {
  return host;
}

/** Subscribe to changes in the roster host. */
export function subscribeRoster(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Read the roster host from a React component. */
export function useRoster(): RosterHost {
  return useSyncExternalStore(subscribeRoster, rosterHost, rosterHost);
}

/** The XP card: the client's own literals and the rules' own level. */
function UnitXpCard({ card }: { card: UnitXpView }): React.JSX.Element {
  return (
    <div className="swl-roster-xp" data-swl-unit-xp="">
      <p className="swl-roster-xp-title">{card.title}</p>
      <p className="swl-roster-xp-name">{card.name}</p>
      <p className="swl-roster-stars" aria-label={`Level ${card.level}`}>
        {card.stars}
      </p>
      <p className="swl-roster-xp-level">
        {card.label} {card.level}
      </p>
      <p className="swl-roster-xp-progress">
        {card.nextLevelXp === null
          ? `Level ${card.maxLevel} reached`
          : `${card.xp} / ${card.nextLevelXp} XP to the next level`}
      </p>
      <p className="swl-roster-xp-bonus">
        +{card.attackBonus} attack · +{card.lifeBonusPercent}% life
      </p>
      <p className="swl-roster-xp-hint">{card.hint}</p>
    </div>
  );
}

/** The team strip: active and deactivated thumbnails, as the server accepted. */
function TeamStrip({ view }: { view: RosterPanelView }): React.JSX.Element {
  return (
    <div className="swl-roster-team">
      <h3 className="swl-roster-heading">Team</h3>
      <p className="swl-roster-note">
        {view.teamAccepted
          ? 'The team the server accepted.'
          : 'The server has not accepted a team yet.'}
      </p>
      {view.thumbnails.length > 0 ? (
        <ul className="swl-roster-thumbs" data-swl-team-thumbs="">
          {view.thumbnails.map((thumb) => (
            <li
              key={thumb.itemId}
              className={
                thumb.active ? 'swl-roster-thumb swl-roster-thumb-active' : 'swl-roster-thumb'
              }
              data-swl-thumb={thumb.itemId}
              data-swl-active={thumb.active ? 'true' : 'false'}
            >
              <span className="swl-roster-thumb-name">{thumb.name}</span>
              <span className="swl-roster-thumb-state">
                {thumb.active ? `in team ×${thumb.count}` : 'deactivated'}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

/** The panel's props, all gestures handed up to the host. */
export interface RosterPanelProps {
  readonly view: RosterPanelView;
  /** The player asked the server to use the composed team. */
  readonly onSubmit?: (team: Army) => void;
  /** The player closed the shared dialog. */
  readonly onCancel: () => void;
}

/**
 * The body the one shared dialog hosts for this family.
 *
 * The count inputs use the same team-picker model as the quest briefing:
 * `initialArmySelection` seeds them and `chooseArmyCount` keeps every change
 * inside both the unit's availability and the shared team budget. A candidate
 * count is still only a gesture; the server re-checks it on receipt.
 */
export function RosterPanel({
  view,
  onSubmit,
  onCancel,
}: RosterPanelProps): React.JSX.Element {
  const [counts, setCounts] = useState<Record<number, number>>(() =>
    initialArmySelection(view.units),
  );
  const [inspected, setInspected] = useState<number | null>(null);
  const cardUnit: RosterUnitView | null =
    view.units.find((unit) => unit.itemId === inspected) ?? view.units[0] ?? null;
  const team: Army = view.units
    .filter((unit) => unit.allowed && (counts[unit.itemId] ?? 0) > 0)
    .map((unit) => ({ unitId: unit.itemId, count: counts[unit.itemId]! }));

  function choose(unit: RosterUnitView, requested: number): void {
    setCounts((previous) =>
      chooseArmyCount(previous, unit.itemId, requested, unit.available),
    );
  }

  return (
    <div className="swl-roster" data-swl-roster="">
      <div className="swl-roster-columns">
        <div className="swl-roster-list">
          <h3 className="swl-roster-heading">Your units</h3>
          {view.units.length === 0 ? (
            <p className="swl-roster-note">No units are available in your army.</p>
          ) : (
            <ul className="swl-roster-units" data-swl-roster-units="">
              {view.units.map((unit) => (
                <li className="swl-roster-unit" key={unit.itemId} data-swl-unit={unit.itemId}>
                  <button
                    type="button"
                    className={
                      cardUnit?.itemId === unit.itemId
                        ? 'swl-roster-inspect swl-roster-inspect-active'
                        : 'swl-roster-inspect'
                    }
                    aria-pressed={cardUnit?.itemId === unit.itemId}
                    onClick={() => setInspected(unit.itemId)}
                  >
                    <span className="swl-roster-unit-name">{unit.name}</span>
                    <span className="swl-roster-unit-qty">×{unit.available}</span>
                    <span className="swl-roster-unit-level">
                      {unit.level > 0 ? '★'.repeat(unit.level) : '—'}
                    </span>
                  </button>
                  <input
                    type="number"
                    min={0}
                    max={unit.available}
                    value={counts[unit.itemId] ?? 0}
                    disabled={!unit.allowed || view.teamAccepted}
                    aria-label={`${unit.name} team count`}
                    onChange={(event) => choose(unit, Number(event.target.value))}
                  />
                  {unit.allowed ? null : (
                    <span className="swl-roster-note">not allowed</span>
                  )}
                </li>
              ))}
            </ul>
          )}
          <TeamStrip view={view} />
        </div>
        {cardUnit ? <UnitXpCard card={cardUnit.card} /> : null}
      </div>
      <div className="swl-roster-actions">
        {onSubmit && team.length > 0 ? (
          <button
            type="button"
            className="swl-roster-primary"
            data-swl-action="send-team"
            disabled={view.teamAccepted}
            onClick={() => onSubmit(team)}
          >
            Use this team
          </button>
        ) : null}
        <button type="button" onClick={onCancel}>
          Close
        </button>
      </div>
    </div>
  );
}
