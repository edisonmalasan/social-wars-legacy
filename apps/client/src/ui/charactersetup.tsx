/**
 * The character-setup / late-era recovery / attack-tooltip panels.
 *
 * Both bodies live in the **one** shared dialog (`dialog.tsx`); this file adds
 * no second modal stack, no local game state and no art. The hospital panel
 * draws only the server's `deadHeroes` and store count with the content's
 * names and costs, and each button is the catalogue's existing
 * `resurrect_hero` request through the one command transport. The server's
 * answer — acceptance or refusal — is drawn by the shared feedback channel;
 * nothing here revives a unit or spends a resource on its own.
 *
 * The attack-symbol panel is the legend behind the original's symbol art: the
 * client's own `RecuadroInfo` sentences and the rules' own damage classes.
 * The proprietary symbols stay excluded.
 */
import type { NativeCommand } from '@swl/client';

import type {
  AttackSymbolsPanelView,
  DeadUnitView,
  HospitalPanelView,
} from './state.ts';

/** The body hosted by the one dialog for this family. */
export type CharacterSetupPanelView =
  | { readonly kind: 'hospital'; readonly view: HospitalPanelView }
  | { readonly kind: 'attack-symbols'; readonly view: AttackSymbolsPanelView };

/** The panel's props. */
export interface CharacterSetupPanelProps {
  /** The server-and-content reading the panel draws. */
  readonly panel: CharacterSetupPanelView;
  /** Send a gesture through the client's one command transport. */
  readonly onCommand?: (command: NativeCommand) => void;
  /** The player asked the shared dialog to close. */
  readonly onCancel?: () => void;
}

/**
 * Show a literal recorded from AS3 source with its escaped newlines and
 * apostrophes as the text the client meant. This is presentation only: the
 * literal itself is compared verbatim with the inventory in the tests.
 */
function displayLiteral(text: string): string {
  return text.replace(/\\n/g, '\n').replace(/\\'/g, "'");
}

/** One dead unit row and its two request gestures. */
function DeadUnitRow({
  unit,
  view,
  onCommand,
}: {
  unit: DeadUnitView;
  view: HospitalPanelView;
  onCommand?: (command: NativeCommand) => void;
}): React.JSX.Element {
  return (
    <li className="swl-hospital-unit" data-swl-dead-unit={unit.itemId}>
      <span className="swl-hospital-unit-name">{unit.name}</span>
      <span className="swl-hospital-unit-count">×{unit.count}</span>
      <span className="swl-hospital-unit-cost">
        {view.resurrectForLabel} {unit.syringes} {view.syringesLabel.toLowerCase()}
      </span>
      <button
        type="button"
        className="swl-hospital-resurrect"
        onClick={() => onCommand?.(unit.resurrect)}
      >
        {view.resurrectLabel}
      </button>
      {unit.resurrectWithSyringe ? (
        <button
          type="button"
          className="swl-hospital-resurrect swl-hospital-resurrect-syringe"
          onClick={() => onCommand?.(unit.resurrectWithSyringe!)}
        >
          {view.syringesLabel}
        </button>
      ) : null}
    </li>
  );
}

/** The hospital's body: server-owned dead units and server-owned syringe count. */
function Hospital({ view, onCommand }: {
  view: HospitalPanelView;
  onCommand?: (command: NativeCommand) => void;
}): React.JSX.Element {
  return (
    <div className="swl-hospital" data-swl-character-setup="hospital">
      <p className="swl-hospital-description">{view.description}</p>
      <p className="swl-hospital-store">
        {view.syringesLabel}: {view.availableLabel} {view.syringesAvailable} · {view.askLabel}
      </p>
      {view.dead.length > 0 ? (
        <ul className="swl-hospital-units">
          {view.dead.map((unit) => (
            <DeadUnitRow
              key={unit.itemId}
              unit={unit}
              view={view}
              onCommand={onCommand}
            />
          ))}
        </ul>
      ) : null}
      <p className="swl-hospital-help" role="note">
        {displayLiteral(view.help)}
      </p>
    </div>
  );
}

/** The attack-symbol legend: client literals and the rules' damage classes. */
function AttackSymbols({
  view,
}: {
  view: AttackSymbolsPanelView;
}): React.JSX.Element {
  return (
    <div className="swl-attack-symbols" data-swl-character-setup="attack-symbols">
      <p className="swl-attack-symbols-heading">{view.heading}</p>
      <dl className="swl-attack-symbols-stats">
        {view.stats.map((stat) => (
          <div className="swl-attack-symbols-stat" key={stat.symbol}>
            <dt>{stat.symbol}</dt>
            <dd>{stat.label}</dd>
          </div>
        ))}
      </dl>
      <p className="swl-attack-symbols-subhead">Damage classes</p>
      <ul className="swl-attack-symbols-classes">
        {view.damageClasses.map((name) => (
          <li key={name}>{name}</li>
        ))}
      </ul>
    </div>
  );
}

/** The one dialog's body for this family, selected by the panel's kind. */
export function CharacterSetupPanel({
  panel,
  onCommand,
  onCancel,
}: CharacterSetupPanelProps): React.JSX.Element {
  return (
    <div className="swl-character-setup">
      {panel.kind === 'hospital' ? (
        <Hospital view={panel.view} onCommand={onCommand} />
      ) : (
        <AttackSymbols view={panel.view} />
      )}
      <div className="swl-character-setup-actions">
        <button type="button" className="swl-character-setup-ok" onClick={onCancel}>
          OK
        </button>
      </div>
    </div>
  );
}
