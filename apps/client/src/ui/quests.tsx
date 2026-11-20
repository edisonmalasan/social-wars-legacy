/**
 * The quest panels, hosted in the one shared dialog.
 *
 * Every value drawn here is a reading of a server answer or of the content:
 * the briefing's titles are the rules', the counters and HP are the server's
 * ledger, and the result is the answer `end_quest` gave. The controls are
 * gestures — they call the host, which sends the request. Nothing in this
 * file can declare a kill, a counter, a win or a reward.
 */
import { useState } from 'react';

import type {
  ActiveQuestView,
  QuestActionChoice,
  QuestBriefing,
  QuestDifficulty,
  QuestResultView,
} from '@swl/client';

/** The panel the shared dialog hosts. */
export type QuestPanelView =
  | { readonly kind: 'briefing'; readonly briefing: QuestBriefing }
  | { readonly kind: 'combat'; readonly active: ActiveQuestView }
  | { readonly kind: 'result'; readonly result: QuestResultView };

/** The quest panel's props. */
export interface QuestPanelProps {
  readonly view: QuestPanelView;
  /** True while a quest request is pending; request buttons are disabled. */
  readonly busy: boolean;
  /** The player asked to start. The host decides which request to send. */
  readonly onStart: (questId: string, difficulty: QuestDifficulty) => void;
  /** The player pressed one of the server's allowed actions. */
  readonly onAction: (questId: string, action: QuestActionChoice) => void;
  /** The player cancelled a briefing, or left a result for the base. */
  readonly onCancel: () => void;
  /** The player asked to retry (or replay) the finished mission. */
  readonly onRetry?: (questId: string) => void;
  /** The player asked to open the next mission the server made available. */
  readonly onNext?: (questId: string) => void;
}

/** The brief, before the player asks the server to start. */
function Briefing({
  briefing,
  busy,
  onStart,
  onCancel,
}: {
  briefing: QuestBriefing;
  busy: boolean;
  onStart: QuestPanelProps['onStart'];
  onCancel: QuestPanelProps['onCancel'];
}): React.JSX.Element {
  // The difficulty is the player's own choice, held only for the length of
  // this panel. It is sent with the start request; the server owns the quest.
  const [difficulty, setDifficulty] = useState<QuestDifficulty>(briefing.difficulty);
  return (
    <div className="swl-quest-panel">
      <p className="swl-quest-subtitle">{briefing.subtitle}</p>
      <fieldset className="swl-quest-difficulty">
        <legend>Difficulty</legend>
        {([1, 2, 3] as const).map((stars) => (
          <label key={stars} className="swl-quest-star">
            <input
              type="radio"
              name={`quest-difficulty-${briefing.questId}`}
              value={stars}
              checked={difficulty === stars}
              onChange={() => setDifficulty(stars)}
            />
            {'★'.repeat(stars)}
          </label>
        ))}
      </fieldset>
      <div className="swl-quest-buttons">
        <button
          type="button"
          className="swl-quest-primary"
          disabled={!briefing.canStart || busy}
          onClick={() => onStart(briefing.questId, difficulty)}
        >
          Start mission
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

/** The authoritative ledger, as the server last answered it. */
function Combat({
  active,
  busy,
  onAction,
}: {
  active: ActiveQuestView;
  busy: boolean;
  onAction: QuestPanelProps['onAction'];
}): React.JSX.Element {
  return (
    <div className="swl-quest-panel">
      <dl className="swl-quest-counters">
        {active.counters.map((counter) => (
          <div key={counter.name} className="swl-quest-counter">
            <dt>{counter.name}</dt>
            <dd>{counter.value}</dd>
          </div>
        ))}
      </dl>
      {active.elements.length > 0 ? (
        <ul className="swl-quest-roster">
          {active.elements.map((element) => (
            <li key={element.ref} className="swl-quest-unit">
              <span>{element.label}</span>
              <span className={element.alive ? '' : 'swl-quest-dead'}>
                {element.alive ? 'alive' : 'destroyed'}
              </span>
              <span>
                HP {element.hp}
                {element.key ? ' · losing element' : ''}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
      <div className="swl-quest-buttons">
        {active.actions.map((action, index) => (
          <button
            key={`${action.kind}:${'ref' in action ? action.ref : index}`}
            type="button"
            data-swl-action={action.kind}
            disabled={!action.enabled || busy}
            onClick={() => onAction(active.questId, action)}
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/** The server's answer to the Finish gesture. */
function Result({
  result,
  busy,
  onRetry,
  onNext,
  onCancel,
}: {
  result: QuestResultView;
  busy: boolean;
  onRetry: QuestPanelProps['onRetry'];
  onNext: QuestPanelProps['onNext'];
  onCancel: QuestPanelProps['onCancel'];
}): React.JSX.Element {
  const next = result.next;
  return (
    <div className="swl-quest-panel">
      <h3 className="swl-quest-result-heading">
        {result.won ? 'Mission complete' : 'Mission failed'}
      </h3>
      <p className={result.won ? 'swl-quest-won' : 'swl-quest-lost'}>{result.message}</p>
      {result.missionComplete && result.rank !== null ? (
        <p className="swl-quest-rank">Rank {result.rank}</p>
      ) : null}
      {result.rewards.length > 0 ? (
        <>
          <p className="swl-quest-reward-title">Rewards granted by the server</p>
          <ul className="swl-quest-rewards" data-swl-rewards="">
            {result.rewards.map((reward, index) => (
              <li key={`${reward.resource}:${index}`} data-swl-reward={reward.resource}>
                {reward.resource} +{reward.amount}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <div className="swl-quest-buttons">
        {next?.available ? (
          <button
            type="button"
            className="swl-quest-primary"
            data-swl-action="next"
            disabled={busy}
            onClick={() => next && onNext?.(next.questId)}
          >
            Next mission: {next.title}
          </button>
        ) : null}
        <button
          type="button"
          data-swl-action="retry"
          disabled={busy}
          onClick={() => onRetry?.(result.questId)}
        >
          {result.won ? 'Replay mission' : 'Retry mission'}
        </button>
        <button type="button" onClick={onCancel}>
          Return to base
        </button>
      </div>
    </div>
  );
}

/** The hosted panel's body. */
export function QuestPanel(props: QuestPanelProps): React.JSX.Element {
  if (props.view.kind === 'briefing') {
    return (
      <Briefing
        briefing={props.view.briefing}
        busy={props.busy}
        onStart={props.onStart}
        onCancel={props.onCancel}
      />
    );
  }
  if (props.view.kind === 'combat') {
    return <Combat active={props.view.active} busy={props.busy} onAction={props.onAction} />;
  }
  return (
    <Result
      result={props.view.result}
      busy={props.busy}
      onRetry={props.onRetry}
      onNext={props.onNext}
      onCancel={props.onCancel}
    />
  );
}
