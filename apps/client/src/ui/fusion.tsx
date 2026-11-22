/**
 * Atom Fusion and the robot-research centres, hosted by the client's one
 * shared dialog.
 *
 * These are the bodies behind `popups/PopupSoulMixer.as` and
 * `popups/PopupResearchCenter.as` (plus their movieclip shells). The pure rules
 * in `@swl/rules` price the power-ups and name the research track; the content
 * supplies the unit names and the `breeding_order` candidates; the server's
 * save supplies the two chosen units, the rolled power, the granted result and
 * the research timestamps. `apps/client/src/ui/state.ts` is the only reader —
 * this file draws what it reads and sends the catalogue commands it is given.
 *
 * Nothing here rolls a fusion, decides an outcome or invents a countdown. A
 * missing server field is drawn as an explicit empty state, and every gesture
 * goes through the host's one command transport, so the server still decides
 * what, if anything, happens. No proprietary art is claimed.
 */
import { useSyncExternalStore } from 'react';

import type { NativeCommand } from '@swl/client';

import {
  ATOM_FUSION_NO_INPUTS,
  ATOM_FUSION_NO_POWER,
  ATOM_FUSION_NO_RESULT,
  ATOM_FUSION_POWERUP_LABEL,
  ATOM_FUSION_SPEEDUP_LABEL,
  RESEARCH_FINISHES_IN,
  RESEARCH_GET_BUTTON,
  RESEARCH_NO_TIMESTAMP,
  RESEARCH_PROGRESS_LABEL,
  RESEARCH_RESEARCH_BUTTON,
  RESEARCH_RESEARCHING,
  type AtomFusionPanelView,
  type FusionDialogKind,
  type ResearchPanelView,
} from './state.ts';

/** The host's only UI-owned state: which of the three screens to open. */
export interface FusionHost {
  readonly open?: (kind: FusionDialogKind) => void;
}

const CLOSED_HOST: FusionHost = {};
let host: FusionHost = CLOSED_HOST;
const listeners = new Set<() => void>();

/** Publish the UI-only gesture the host chose. */
export function setFusionHost(patch: Partial<FusionHost>): void {
  host = { ...host, ...patch };
  for (const listener of listeners) listener();
}

/** The current UI-only fusion slot. */
export function fusionHost(): FusionHost {
  return host;
}

/** Subscribe to changes in the fusion slot. */
export function subscribeFusion(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Read the fusion slot from a React component. */
export function useFusion(): FusionHost {
  return useSyncExternalStore(subscribeFusion, fusionHost, fusionHost);
}

/** A launcher for the three panels, each with its own shared-dialog id. */
export function FusionLauncher(): React.JSX.Element {
  const { open } = useFusion();
  return (
    <details className="swl-fusion-launcher">
      <summary className="swl-fusion-launcher-summary">Fusion &amp; research</summary>
      <div className="swl-fusion-launcher-list">
        <button type="button" className="swl-fusion-launch" data-swl-screen="atom" onClick={() => open?.('atom')}>
          Atom Fusion
        </button>
        <button type="button" className="swl-fusion-launch" data-swl-screen="area51" onClick={() => open?.(0)}>
          AREA 51
        </button>
        <button type="button" className="swl-fusion-launch" data-swl-screen="robotic" onClick={() => open?.(1)}>
          Robotic Center
        </button>
      </div>
    </details>
  );
}

/** One request button. The command is the catalogue's; the server decides. */
function CommandButton({
  command,
  className,
  label,
  onCommand,
}: {
  readonly command: NativeCommand;
  readonly className: string;
  readonly label: string;
  readonly onCommand?: (command: NativeCommand) => void;
}): React.JSX.Element {
  return (
    <button
      type="button"
      className={`swl-fusion-action ${className}`}
      data-swl-command={command.name}
      onClick={() => onCommand?.(command)}
    >
      {label}
    </button>
  );
}

/**
 * The Atom Fusion body: the content's candidate preview, the two units the
 * server says are in the mixer, the power only when it was published, the
 * rules' power-up price table, and the result only when the server granted one.
 */
export function AtomFusionPanel({
  view,
  onCommand,
  onClose,
}: {
  readonly view: AtomFusionPanelView;
  readonly onCommand?: (command: NativeCommand) => void;
  readonly onClose?: () => void;
}): React.JSX.Element {
  return (
    <div className="swl-fusion" data-swl-fusion="atom">
      <p className="swl-fusion-title">{view.title}</p>
      <p className="swl-fusion-description">{view.description}</p>

      <section className="swl-fusion-inputs" data-swl-fusion-inputs>
        <h3>Selected units</h3>
        {view.inputs.length === 0 ? (
          <p className="swl-fusion-empty">{ATOM_FUSION_NO_INPUTS}</p>
        ) : (
          <ul className="swl-fusion-input-list">
            {view.inputs.map((input, index) => (
              <li key={`${index}:${input.itemId}`} data-swl-input={input.itemId}>
                {input.name}
                {input.power !== null ? ` · power ${input.power}` : ''}
              </li>
            ))}
          </ul>
        )}
        {view.gateMessage ? (
          <p className="swl-fusion-gate" role="status">
            {view.gateMessage}
          </p>
        ) : null}
      </section>

      <section className="swl-fusion-power" data-swl-fusion-power>
        <h3>Result power</h3>
        {view.powerPreview !== null ? (
          <p className="swl-fusion-power-value" data-swl-power={view.powerPreview}>
            {view.powerPreview}
          </p>
        ) : (
          <p className="swl-fusion-empty">{ATOM_FUSION_NO_POWER}</p>
        )}
      </section>

      <section className="swl-fusion-candidates" data-swl-fusion-candidates>
        <h3>Candidates ({view.candidates.length})</h3>
        <ul className="swl-fusion-candidate-list">
          {view.candidates.map((candidate) => (
            <li key={candidate.itemId} data-swl-candidate={candidate.itemId} data-swl-power={candidate.power}>
              {candidate.name} · {candidate.power}
            </li>
          ))}
        </ul>
      </section>

      <section className="swl-fusion-powerups" data-swl-fusion-powerups>
        <h3>{ATOM_FUSION_POWERUP_LABEL}</h3>
        <table className="swl-fusion-powerup-table">
          <thead>
            <tr>
              <th>Level</th>
              <th>Cash</th>
              <th>Order +</th>
              <th>Request</th>
            </tr>
          </thead>
          <tbody>
            {view.powerupRows.map((row) => (
              <tr key={row.level} data-swl-level={row.level} data-swl-current={row.current}>
                <td>{row.level}</td>
                <td>{row.cashCost}</td>
                <td>{row.orderIncrement}</td>
                <td>
                  {view.inputs.length === 2 && !view.gateMessage ? (
                    <CommandButton
                      command={row.command}
                      className="swl-fusion-powerup"
                      label={`${ATOM_FUSION_POWERUP_LABEL} · ${row.cashCost}`}
                      onCommand={onCommand}
                    />
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="swl-fusion-result" data-swl-fusion-result role="status">
        <h3>Granted by the server</h3>
        {view.result ? (
          <p className="swl-fusion-result-value" data-swl-granted={view.result.itemId}>
            {view.result.name}
            {view.result.power !== null ? ` · power ${view.result.power}` : ''}
          </p>
        ) : (
          <p className="swl-fusion-empty">{ATOM_FUSION_NO_RESULT}</p>
        )}
      </section>

      {view.speedup ? (
        <CommandButton
          command={view.speedup}
          className="swl-fusion-speedup"
          label={ATOM_FUSION_SPEEDUP_LABEL}
          onCommand={onCommand}
        />
      ) : null}
      <button type="button" className="swl-fusion-close" onClick={onClose}>
        Close
      </button>
    </div>
  );
}

/** The Area 51 / Robotic Center body, drawn from the server's research save. */
export function ResearchPanel({
  view,
  onCommand,
  onClose,
}: {
  readonly view: ResearchPanelView;
  readonly onCommand?: (command: NativeCommand) => void;
  readonly onClose?: () => void;
}): React.JSX.Element {
  const canCollect = view.collectCommand !== null;
  return (
    <div className="swl-research" data-swl-research={view.type}>
      <p className="swl-research-title">{view.title}</p>

      <section className="swl-research-progress" data-swl-research-progress>
        <p className="swl-research-progress-label">
          {view.progressLabel}: {view.step ?? '—'}/{view.totalSteps}
        </p>
        <div
          className="swl-research-bar"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={view.totalSteps}
          aria-valuenow={view.step ?? 0}
        >
          <span
            className="swl-research-bar-fill"
            style={{ width: `${Math.min(100, Math.max(0, ((view.step ?? 0) / view.totalSteps) * 100))}%` }}
          />
        </div>
      </section>

      <section className="swl-research-item" data-swl-research-item>
        <h3>{view.researchingLabel}</h3>
        {view.item ? (
          <>
            <p className="swl-research-item-name" data-swl-item={view.item.id}>
              {view.item.name}
            </p>
            <p className="swl-research-item-cash">{view.item.cash} cash</p>
          </>
        ) : (
          <p className="swl-fusion-empty">No research item has been published by the server.</p>
        )}
        <ul className="swl-research-track">
          {view.track.map((entry) => (
            <li key={entry.id} data-swl-track={entry.id} data-swl-current={entry.current}>
              {entry.name}
            </li>
          ))}
        </ul>
      </section>

      <section className="swl-research-countdown" data-swl-research-countdown role="status">
        <p className="swl-research-countdown-label">{view.finishesInLabel}</p>
        {view.countdown ? (
          <p className="swl-research-countdown-value" data-swl-seconds={view.countdown.secondsRemaining}>
            {view.countdown.label}
            {view.countdown.due ? ' · ready' : ''}
          </p>
        ) : (
          <p className="swl-fusion-empty">{RESEARCH_NO_TIMESTAMP}</p>
        )}
      </section>

      <p className="swl-research-hint">{view.hint}</p>

      {view.friendHelp ? (
        <section className="swl-research-help" data-swl-research-help role="status">
          <p className="swl-research-help-title">{view.friendHelp.message}</p>
          <p className="swl-research-help-hint">{view.friendHelp.hint}</p>
          <ul className="swl-research-help-friends">
            {view.friendHelp.friends.map((friend) => (
              <li key={friend} data-swl-friend={friend}>
                {friend}
              </li>
            ))}
          </ul>
          <CommandButton
            command={view.friendHelp.command}
            className="swl-research-hire"
            label={view.friendHelp.button}
            onCommand={onCommand}
          />
        </section>
      ) : null}

      <div className="swl-research-actions">
        {canCollect && view.collectCommand ? (
          <CommandButton
            command={view.collectCommand}
            className="swl-research-get"
            label={RESEARCH_GET_BUTTON}
            onCommand={onCommand}
          />
        ) : (
          <CommandButton
            command={view.researchCommand}
            className="swl-research-next"
            label={RESEARCH_RESEARCH_BUTTON}
            onCommand={onCommand}
          />
        )}
        {view.speedupCommand ? (
          <CommandButton
            command={view.speedupCommand}
            className="swl-research-speedup"
            label={`Speed up for ${view.item?.cash ?? 0}`}
            onCommand={onCommand}
          />
        ) : null}
      </div>
      <button type="button" className="swl-fusion-close" onClick={onClose}>
        Close
      </button>
    </div>
  );
}
