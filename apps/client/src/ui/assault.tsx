/**
 * The assault result, battle-history and combat-HUD panels.
 *
 * These are the screens behind the shared dialog, in the same shape as the
 * quest panels: a view the host derives from the server's answer, a `busy`
 * flag for pending requests, and gestures that call the host. Every number,
 * outcome, history row, loot row, strategy choice and charge here is a reading
 * of what the server actually answered. Nothing in this file runs a battle,
 * rolls loot, writes history or declares a special attack ready.
 */
import { useState } from 'react';

import type {
  AssaultCountdownView,
  AssaultHistoryEntry,
  AssaultHistoryView,
  ArmyUnitView,
  NativeCommand,
  SpecialAttackChargeView,
} from '@swl/client';

import type { AssaultResultPanelView, BattleOptionsPanelView } from './state.ts';

/** The panel the shared dialog hosts. */
export type AssaultPanelView =
  | { readonly kind: 'result'; readonly view: AssaultResultPanelView }
  | {
      readonly kind: 'history';
      readonly view: AssaultHistoryView;
      readonly countdown: AssaultCountdownView | null;
    }
  | { readonly kind: 'options'; readonly view: BattleOptionsPanelView }
  | {
      readonly kind: 'hud';
      readonly countdown: AssaultCountdownView | null;
      readonly specialAttacks: readonly SpecialAttackChargeView[];
    };

/** The assault panels' props, following the quest panels' gesture pattern. */
export interface AssaultPanelProps {
  readonly panel: AssaultPanelView;
  /** True while an assault request is pending; request buttons are disabled. */
  readonly busy: boolean;
  /** The player asked to send a command; the host owns the transport. */
  readonly onCommand?: (command: NativeCommand) => void;
  /** The player dismissed the dialog. */
  readonly onCancel: () => void;
}

/** The original shows only the last ten attacks; do not imply it shows more. */
const HISTORY_LIMIT = 10;

/** A server timestamp in words, or an em dash when the server gave none. */
function clock(at: number | null): string {
  if (at === null) return '—';
  const date = new Date(at * 1000);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toISOString().slice(0, 16).replace('T', ' ');
}

/** A whole-second countdown in words. Presentation only. */
function duration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, '0')}`;
}

/** The server's attack-reset countdown, when it published one. */
function AssaultTimer({ countdown }: { countdown: AssaultCountdownView | null }): React.JSX.Element | null {
  if (!countdown) return null;
  return (
    <p className="swl-assault-countdown" role="timer">
      Attacks reset in {duration(countdown.secondsRemaining)}
    </p>
  );
}

/**
 * The attack-result popup.
 *
 * The win/loss line and the loot rows are the server's receipt; an unsettled
 * answer draws no loot row. The army list is the server's roster, named by the
 * content — the "Your Army" side of the original result screen.
 */
function Result({
  view,
  onCancel,
}: {
  view: AssaultResultPanelView;
  onCancel: AssaultPanelProps['onCancel'];
}): React.JSX.Element {
  const { result, army } = view;
  const showCounts = result.unitsAlive !== null || result.unitsDead !== null;
  return (
    <div className="swl-assault-panel" data-swl-assault="result">
      <h3 className={result.won ? 'swl-assault-won' : 'swl-assault-lost'}>
        {result.won ? 'You won' : 'You lost'}
      </h3>
      {result.settled ? null : (
        <p className="swl-assault-note">
          The server recorded the outcome but published no loot receipt.
        </p>
      )}
      {result.loot.length > 0 ? (
        <>
          <p className="swl-assault-heading">You won:</p>
          <ul className="swl-assault-loot" data-swl-rewards="">
            {result.loot.map((row, index) => (
              <li key={`${row.resource}:${index}`} data-swl-reward={row.resource}>
                {row.resource} +{row.amount}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {showCounts ? (
        <dl className="swl-assault-counts">
          {result.unitsAlive !== null ? (
            <div className="swl-assault-count">
              <dt>Units Alive</dt>
              <dd>{result.unitsAlive}</dd>
            </div>
          ) : null}
          {result.unitsDead !== null ? (
            <div className="swl-assault-count">
              <dt>Units Dead</dt>
              <dd>{result.unitsDead}</dd>
            </div>
          ) : null}
        </dl>
      ) : null}
      {result.opponent !== null ? (
        <p className="swl-assault-opponent">Opponent: {result.opponent}</p>
      ) : null}
      {army.length > 0 ? (
        <section className="swl-assault-army" data-swl-roster="">
          <h4>Your Army</h4>
          <ul className="swl-assault-roster">
            {army.map((unit: ArmyUnitView) => (
              <li key={unit.itemId} className="swl-assault-roster-row">
                <span>{unit.name}</span>
                <span>×{unit.available}</span>
                {unit.allowed ? null : <span className="swl-assault-muted">not allowed</span>}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <div className="swl-assault-buttons">
        <button type="button" className="swl-assault-primary" data-swl-action="ok" onClick={onCancel}>
          OK
        </button>
      </div>
    </div>
  );
}

/** One row of the battle history, with dashes where the server said nothing. */
function HistoryRow({ row }: { row: AssaultHistoryEntry }): React.JSX.Element {
  return (
    <tr>
      <td>{clock(row.at)}</td>
      <td>{row.opponent ?? '—'}</td>
      <td>{row.won === null ? '—' : row.won ? 'Won' : 'Lost'}</td>
      <td>{row.gold === null ? '—' : row.gold}</td>
    </tr>
  );
}

/** The assault-history popup: only the attacks the server actually answered. */
function History({
  view,
  countdown,
  onCancel,
}: {
  view: AssaultHistoryView;
  countdown: AssaultCountdownView | null;
  onCancel: AssaultPanelProps['onCancel'];
}): React.JSX.Element {
  const [tab, setTab] = useState<'sent' | 'received'>('sent');
  const rows = (tab === 'sent' ? view.sent : view.received).slice(0, HISTORY_LIMIT);
  return (
    <div className="swl-assault-panel" data-swl-assault="history">
      <AssaultTimer countdown={countdown} />
      <div className="swl-assault-tabs" role="tablist" aria-label="Battle results">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'sent'}
          className={tab === 'sent' ? 'swl-assault-tab-active' : 'swl-assault-tab'}
          data-swl-tab="sent"
          onClick={() => setTab('sent')}
        >
          Attacks Sent
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'received'}
          className={tab === 'received' ? 'swl-assault-tab-active' : 'swl-assault-tab'}
          data-swl-tab="received"
          onClick={() => setTab('received')}
        >
          Attacks received
        </button>
      </div>
      <p className="swl-assault-note">(showing only last 10 attacks)</p>
      <table className="swl-assault-history">
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Opponent</th>
            <th scope="col">Result</th>
            <th scope="col">Gold</th>
          </tr>
        </thead>
        <tbody data-swl-history={tab}>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={4} className="swl-assault-muted">No attacks recorded by the server.</td>
            </tr>
          ) : (
            rows.map((row, index) => <HistoryRow key={index} row={row} />)
          )}
        </tbody>
      </table>
      <div className="swl-assault-buttons">
        <button type="button" className="swl-assault-primary" data-swl-action="ok" onClick={onCancel}>
          OK
        </button>
      </div>
    </div>
  );
}

/** The battle-options popup: four strategies, one server-owned choice. */
function Options({
  view,
  busy,
  onCommand,
  onCancel,
}: {
  view: BattleOptionsPanelView;
  busy: boolean;
  onCommand: AssaultPanelProps['onCommand'];
  onCancel: AssaultPanelProps['onCancel'];
}): React.JSX.Element {
  const [choice, setChoice] = useState<number>(view.selected ?? 0);
  return (
    <div className="swl-assault-panel" data-swl-assault="options">
      <fieldset className="swl-assault-strategies">
        <legend>Defensive</legend>
        {view.options.map((option) => (
          <label key={option.strategy} className="swl-assault-strategy">
            <input
              type="radio"
              name="assault-strategy"
              value={option.strategy}
              checked={choice === option.strategy}
              disabled={busy || view.selected === null}
              onChange={() => setChoice(option.strategy)}
            />
            <span className="swl-assault-strategy-name">{option.name}</span>
            <span className="swl-assault-strategy-note">{option.description}</span>
          </label>
        ))}
      </fieldset>
      <div className="swl-assault-buttons">
        <button
          type="button"
          className="swl-assault-primary"
          data-swl-action="set_strategy"
          disabled={busy || view.selected === null || choice === 0}
          onClick={() => {
            const option = view.options.find((entry) => entry.strategy === choice);
            if (option) onCommand?.(option.command);
          }}
        >
          OK
        </button>
        <button type="button" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

/**
 * One special-attack portrait. The ready label and the casting mask are
 * readings of the server's charge view; when it publishes no value the tile
 * says so rather than inventing a charge or a ready state.
 */
function SpecialPortrait({ attack }: { attack: SpecialAttackChargeView }): React.JSX.Element {
  const label =
    attack.ready === null
      ? attack.limit
        ? 'not charged yet'
        : 'Charge state not published by the server'
      : attack.ready
        ? 'Ready'
        : 'Not ready yet!';
  return (
    <li
      className={`swl-assault-special${attack.ready === false ? ' swl-assault-special-idle' : ''}`}
      data-swl-special={attack.id}
    >
      <span className="swl-assault-special-name">{attack.id}</span>
      <span className="swl-assault-special-shape">{attack.shape}</span>
      <span className="swl-assault-special-track" aria-hidden="true">
        <span
          className="swl-assault-special-mask"
          style={{ width: `${(attack.charge ?? 0) * 100}%` }}
        />
      </span>
      <span className="swl-assault-special-state">{label}</span>
    </li>
  );
}

/** The combat HUD: the server's timer and only its published charge records. */
function Hud({
  countdown,
  specialAttacks,
  onCancel,
}: {
  countdown: AssaultCountdownView | null;
  specialAttacks: readonly SpecialAttackChargeView[];
  onCancel: AssaultPanelProps['onCancel'];
}): React.JSX.Element {
  return (
    <div className="swl-assault-panel" data-swl-assault="hud">
      <AssaultTimer countdown={countdown} />
      {specialAttacks.length === 0 ? (
        <p className="swl-assault-note">The server has not published special-attack charge state.</p>
      ) : (
        <ul className="swl-assault-specials" data-swl-specials="">
          {specialAttacks.map((attack) => (
            <SpecialPortrait key={attack.id} attack={attack} />
          ))}
        </ul>
      )}
      <div className="swl-assault-buttons">
        <button type="button" onClick={onCancel}>Close</button>
      </div>
    </div>
  );
}

/** The hosted panel's body, one of the four assault-family screens. */
export function AssaultPanel(props: AssaultPanelProps): React.JSX.Element {
  if (props.panel.kind === 'result') {
    return <Result view={props.panel.view} onCancel={props.onCancel} />;
  }
  if (props.panel.kind === 'history') {
    return (
      <History
        view={props.panel.view}
        countdown={props.panel.countdown}
        onCancel={props.onCancel}
      />
    );
  }
  if (props.panel.kind === 'options') {
    return (
      <Options
        view={props.panel.view}
        busy={props.busy}
        onCommand={props.onCommand}
        onCancel={props.onCancel}
      />
    );
  }
  return (
    <Hud
      countdown={props.panel.countdown}
      specialAttacks={props.panel.specialAttacks}
      onCancel={props.onCancel}
    />
  );
}
