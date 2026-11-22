/**
 * The soul-mixer help and turbine, hosted by the client's one shared dialog.
 *
 * This is presentation only. `popups/PopupSoulMixerHelp.as` writes four lines
 * of help text; the four steps below are that literal, verbatim. The text
 * mentions POWERUP and SPEEDUP, but the panel offers neither gesture: those
 * commands have no authoritative answer (no applier case, no recovered output
 * rule, and no price for soulmixer_speedup). The larger fusion and breeding
 * screens stay planned.
 *
 * `popups/SoulMixer/SoulMixerTurbina.as` has only a `setState` method — its
 * timer is the server's. The panel reads that state from the world when the
 * server has published one and otherwise draws a clearly labelled empty
 * state. It never computes or invents a countdown.
 *
 * The host owns only the UI gesture of opening the dialog; all values are
 * read from the server's world and the decompiled copy.
 */
import { useSyncExternalStore } from 'react';

import type { WorldSnapshot } from '@swl/client';

import {
  SOUL_MIXER_HELP,
  SOUL_MIXER_TURBINA_LABEL,
  SOUL_MIXER_TURBINA_PLACEHOLDER,
  formatTurbinaRemaining,
  soulMixerTurbina,
} from './state.ts';

/** The host's only UI-owned state: the gesture that opens the dialog. */
export interface SoulMixerHost {
  readonly open?: () => void;
}

const CLOSED_HOST: SoulMixerHost = {};
let host: SoulMixerHost = CLOSED_HOST;
const listeners = new Set<() => void>();

/** Publish the UI-only gesture the host chose. */
export function setSoulMixerHost(patch: Partial<SoulMixerHost>): void {
  host = { ...host, ...patch };
  for (const listener of listeners) listener();
}

/** The current UI-only soul-mixer slot. */
export function soulMixerHost(): SoulMixerHost {
  return host;
}

/** Subscribe to changes in the soul-mixer slot. */
export function subscribeSoulMixer(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Read the soul-mixer slot from a React component. */
export function useSoulMixer(): SoulMixerHost {
  return useSyncExternalStore(subscribeSoulMixer, soulMixerHost, soulMixerHost);
}

/** A small launcher so the recovered help can be opened from the game. */
export function SoulMixerLauncher(): React.JSX.Element {
  const { open } = useSoulMixer();
  return (
    <button type="button" className="swl-soulmixer-launch" onClick={() => open?.()}>
      Soul Mixer
    </button>
  );
}

/**
 * The body hosted by the one dialog: the recovered help copy and the turbine
 * state. The only gesture is Close; no Powerup, Speedup or Fusion button is
 * drawn because the server has no authoritative answer for those commands.
 */
export function SoulMixerPanel({
  world,
  onClose,
}: {
  readonly world: WorldSnapshot;
  readonly onClose?: () => void;
}): React.JSX.Element {
  const turbine = soulMixerTurbina(world);
  return (
    <div className="swl-soulmixer" data-swl-soulmixer="help">
      <p className="swl-soulmixer-help" data-swl-soulmixer-help="steps">
        {SOUL_MIXER_HELP}
      </p>
      <div
        className="swl-soulmixer-turbina"
        data-swl-turbina-available={turbine.available}
        role="status"
      >
        <p className="swl-soulmixer-turbina-label">{SOUL_MIXER_TURBINA_LABEL}</p>
        {turbine.available ? (
          <p className="swl-soulmixer-turbina-state">
            {turbine.state ?? 'Active'}
            {turbine.remainingSeconds !== null
              ? ` · ${formatTurbinaRemaining(turbine.remainingSeconds)}`
              : ''}
          </p>
        ) : (
          <p className="swl-soulmixer-turbina-empty">
            {SOUL_MIXER_TURBINA_PLACEHOLDER}
          </p>
        )}
      </div>
      <button type="button" className="swl-soulmixer-close" onClick={onClose}>
        Close
      </button>
    </div>
  );
}
