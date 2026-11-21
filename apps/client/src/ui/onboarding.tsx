/**
 * The intro / help / mission-info / next-mission / confirmation family.
 *
 * Every one of these is a **body hosted by the one shared dialog** in
 * `dialog.tsx`; this file never creates a second modal. The model behind each
 * body is in `state.ts`, and the values it draws are the client's own
 * tutorial steps (`packages/client/src/tutorial.ts`) and the authoritative
 * quest briefing/result (`packages/client/src/questview.ts`). The buttons are
 * gestures: they call the host, which asks the server. A yes here never
 * settles a quest, a reward or a tutorial step by itself.
 *
 * The host is `main.ts`. It publishes its gestures through the small store
 * below so the root can draw the launcher and the body without a second
 * mounting path; the store holds UI state only — never a world, an outcome or
 * a decision.
 */
import { useSyncExternalStore } from 'react';

import type { QuestDifficulty } from '@swl/client';
import type { Army } from '@swl/rules';

import { QuestPanel } from './quests.tsx';
import type {
  ConfirmView,
  NextMissionView,
  OnboardingPanelKind,
  OnboardingPanelView,
  TutorialHelpView,
} from './state.ts';

/** The callbacks the host publishes for this family. */
export interface OnboardingHost {
  /** The body currently hosted by the shared dialog. */
  readonly view: OnboardingPanelView | null;
  /** Open one of the five panels, each with its own gesture/id. */
  readonly open: ((kind: OnboardingPanelKind) => void) | null;
  /** Ask the server to start a briefed mission. */
  readonly start: ((questId: string, difficulty: QuestDifficulty, team?: Army) => void) | null;
  /** Open the next mission the server made available. */
  readonly next: ((questId: string) => void) | null;
  /** Ask the host to confirm skipping the tutorial. */
  readonly skip: (() => void) | null;
  /** The YES of the confirmation panel, chosen by the host. */
  readonly confirm: (() => void) | null;
}

const CLOSED_HOST: OnboardingHost = {
  view: null,
  open: null,
  start: null,
  next: null,
  skip: null,
  confirm: null,
};

let host: OnboardingHost = CLOSED_HOST;
const listeners = new Set<() => void>();

/** Publish (or clear) the host's gestures and the panel body. */
export function setOnboardingHost(patch: Partial<OnboardingHost>): void {
  host = { ...host, ...patch };
  for (const listener of listeners) listener();
}

/** The current UI-only onboarding state. */
export function onboardingHost(): OnboardingHost {
  return host;
}

/** Subscribe to changes in the onboarding UI state. */
export function subscribeOnboarding(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Read the onboarding UI state from a React component. */
export function useOnboarding(): OnboardingHost {
  return useSyncExternalStore(subscribeOnboarding, onboardingHost, onboardingHost);
}

/** The launcher: one distinct gesture per panel, no game state behind it. */
export function OnboardingLauncher({
  onOpen,
}: {
  onOpen?: (kind: OnboardingPanelKind) => void;
}): React.JSX.Element | null {
  if (!onOpen) return null;
  const entries: readonly [OnboardingPanelKind, string][] = [
    ['intro', 'Intro'],
    ['help', 'Help'],
    ['mission', 'Mission info'],
    ['next', 'Next mission'],
    ['confirm', 'Confirm'],
  ];
  return (
    <div className="swl-onboarding-launcher" aria-label="Game guides">
      {entries.map(([kind, label]) => (
        <button
          key={kind}
          type="button"
          data-swl-onboarding-open={kind}
          onClick={() => onOpen(kind)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

/** The intro and help panels: the tutorial's own steps, in its own words. */
function TutorialHelp({
  view,
  onSkip,
}: {
  view: TutorialHelpView;
  onSkip?: () => void;
}): React.JSX.Element {
  const canSkip = view.steps.some((step) => step.skippable);
  return (
    <div className="swl-onboarding-help" data-swl-onboarding-body="tutorial">
      <p className="swl-tutorial-step">
        STEP {view.currentPosition || 1} OF {view.total}
      </p>
      {view.total === 0 ? <p className="swl-onboarding-empty">No tutorial steps.</p> : null}
      <ol className="swl-onboarding-steps">
        {view.steps.map((step) => (
          <li
            key={step.step}
            className={step.current ? 'swl-onboarding-step-current' : undefined}
            data-swl-step={step.step}
          >
            <p className="swl-tutorial-step">
              STEP {step.position} OF {view.total}
            </p>
            {step.title ? <h3 className="swl-tutorial-title">{step.title}</h3> : null}
            {step.lesson.split('\n').map((line, index) => (
              <p key={index} className="swl-tutorial-lesson">
                {line}
              </p>
            ))}
          </li>
        ))}
      </ol>
      {canSkip && onSkip ? (
        <div className="swl-onboarding-actions">
          <button type="button" data-swl-action="skip" onClick={onSkip}>
            Skip tutorial
          </button>
        </div>
      ) : null}
    </div>
  );
}

/** The server's own next-mission reading, offered as a gesture. */
function NextMission({
  view,
  onNext,
}: {
  view: NextMissionView;
  onNext?: OnboardingHost['next'];
}): React.JSX.Element {
  return (
    <div className="swl-onboarding-next" data-swl-onboarding-body="next">
      <h3 className="swl-quest-result-heading">{view.title}</h3>
      <p className="swl-onboarding-note">Mission {view.index}</p>
      <p className={view.won ? 'swl-quest-won' : 'swl-quest-lost'}>
        {view.won ? 'Mission complete' : 'Mission failed'}
      </p>
      {view.won && view.rank !== null ? (
        <p className="swl-quest-rank">Rank {view.rank}</p>
      ) : null}
      {view.rewards.length > 0 ? (
        <ul className="swl-quest-rewards" data-swl-rewards="">
          {view.rewards.map((reward, index) => (
            <li key={`${reward.resource}:${index}`} data-swl-reward={reward.resource}>
              {reward.resource} +{reward.amount}
            </li>
          ))}
        </ul>
      ) : null}
      <div className="swl-onboarding-actions">
        <button
          type="button"
          className="swl-onboarding-primary"
          data-swl-action="next"
          disabled={!view.available || !onNext}
          onClick={() => onNext?.(view.questId)}
        >
          Open next mission
        </button>
      </div>
    </div>
  );
}

/** A yes/no gate on a request the host will send if the player agrees. */
function Confirm({
  view,
  onConfirm,
  onCancel,
}: {
  view: ConfirmView;
  onConfirm?: OnboardingHost['confirm'];
  onCancel: () => void;
}): React.JSX.Element {
  return (
    <div className="swl-onboarding-confirm" data-swl-onboarding-body="confirm">
      <p className="swl-onboarding-confirm-message">{view.message}</p>
      <div className="swl-onboarding-actions">
        <button type="button" data-swl-action="no" onClick={onCancel}>
          {view.no}
        </button>
        <button
          type="button"
          className="swl-onboarding-primary"
          data-swl-action="yes"
          disabled={!onConfirm}
          onClick={() => onConfirm?.()}
        >
          {view.yes}
        </button>
      </div>
    </div>
  );
}

/** The panel's props, all gestures handed up to the host. */
export interface OnboardingPanelProps {
  readonly view: OnboardingPanelView;
  readonly onCancel: () => void;
  readonly onStart?: OnboardingHost['start'];
  readonly onNext?: OnboardingHost['next'];
  readonly onSkip?: () => void;
  readonly onConfirm?: () => void;
}

/** The body the one shared dialog hosts for this family. */
export function OnboardingPanel({
  view,
  onCancel,
  onStart,
  onNext,
  onSkip,
  onConfirm,
}: OnboardingPanelProps): React.JSX.Element {
  if (view.kind === 'intro' || view.kind === 'help') {
    return <TutorialHelp view={view.view} onSkip={onSkip} />;
  }
  if (view.kind === 'mission') {
    // The briefing is the very model quests.tsx draws, so its team picker,
    // difficulty and Start gesture stay in one place. Start is still the
    // host's request; the server decides whether the mission may begin.
    return (
      <QuestPanel
        view={{ kind: 'briefing', briefing: view.view }}
        busy={false}
        onStart={onStart ?? (() => {})}
        onAction={() => {}}
        onCancel={onCancel}
      />
    );
  }
  if (view.kind === 'next') {
    return <NextMission view={view.view} onNext={onNext} />;
  }
  return <Confirm view={view.view} onConfirm={onConfirm} onCancel={onCancel} />;
}
