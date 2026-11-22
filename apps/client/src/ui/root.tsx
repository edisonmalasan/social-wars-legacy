/**
 * The interface's root.
 *
 * It is the whole of the interface in one place: the **HUD** across the
 * top and the **build menu** in the corner. Both are drawn from the
 * server's answer and from the content, and neither decides anything:
 * the numbers are the server's, and the menu is a list of what the
 * player could ask for.
 *
 * The state is derived here rather than passed in, because the HUD's
 * numbers are a **reading** of the world: the resources are the
 * server's, and the limits are the content's.
 */
import { useMemo, useState } from 'react';

import {
  CLOSED_DIALOG,
  activeQuestState,
  type ArmyUnitView,
  bonusPanel,
  hudState,
  levelOf,
  questChoices,
  type DialogState,
  type FeedbackMessage,
  type ItemType,
  type NativeCommand,
  type Neighbour,
  type QuestActionChoice,
  type QuestChoice,
  type QuestDifficulty,
  type StoredItemView,
  type WorldSnapshot,
} from '@swl/client';
import type { Army } from '@swl/rules';
import type { ContentBundle } from '@swl/content';

import { AssaultPanel, type AssaultPanelView } from './assault.tsx';
import { BuildMenu } from './buildmenu.tsx';
import {
  CharacterSetupPanel,
  type CharacterSetupPanelView,
} from './charactersetup.tsx';
import { Chapters } from './chapters.tsx';
import { ChromeDock, ChromePopupBody, useChrome } from './chrome.tsx';
import { Dialog } from './dialog.tsx';
import { Expansion } from './expansion.tsx';
import { Feedback } from './feedback.tsx';
import { AtomFusionPanel, FusionLauncher, ResearchPanel } from './fusion.tsx';
import { Goals } from './goals.tsx';
import { Hud } from './hud.tsx';
import { InfoPanel, ProductionSelector, PRODUCTION_DIALOG_ID } from './info.tsx';
import { Inventory } from './inventory.tsx';
import { MagicLab } from './magiclab.tsx';
import { closeMarketPanel, MarketPanel, useMarket } from './market.tsx';
import { MysteryLauncher, MysteryPanel, useMystery } from './mystery.tsx';
import { Neighbours } from './neighbours.tsx';
import { OnboardingLauncher, OnboardingPanel, useOnboarding } from './onboarding.tsx';
import {
  OriginalArtGallery,
  OriginalArtLauncher,
  originalArtDialog,
} from './originalart.tsx';
import {
  ORIGINAL_FX_DIALOG_ID,
  OriginalFxGallery,
  OriginalFxLauncher,
  originalFxDialog,
} from './originalfx.tsx';
import {
  AssaultPortraits,
  ExtendedPortraitButton,
  IconPanel,
  PORTRAIT_DIALOG_ID,
  portraitDialog,
  PortraitPopupBody,
} from './portraitshells.tsx';
import { QuestPanel, type QuestPanelView } from './quests.tsx';
import { RecruitPanel } from './recruit.tsx';
import {
  closeResourceButtonsPanel,
  ResourceButtonsPanel,
  useResourceButtons,
} from './resourcebuttons.tsx';
import { RosterPanel, useRoster } from './roster.tsx';
import { SoulMixerLauncher, SoulMixerPanel } from './soulmixerhelp.tsx';
import { SpellBook } from './spellbook.tsx';
import { Store } from './store.tsx';
import { TutorialOverlay, type TutorialOverlayProps } from './tutorial.tsx';
import {
  assaultHistoryPanel,
  assaultHudPanel,
  assaultPortraitPanel,
  assaultResultPanel,
  attackSymbolsPanel,
  atomFusionPanel,
  battleOptionsPanel,
  buildingInfo,
  buildItems,
  categories,
  collectionsPanel,
  expansionPanel,
  extendedPortraitPopup,
  hospitalPanel,
  goalList,
  hudInput,
  infoPanel,
  inventoryItems,
  marketDialog,
  marketPanel,
  type ProductionPanelView,
  questMinLevels,
  questRanks,
  recruitView,
  resourceIconPanel,
  researchPanel,
  resourceButtonsDialog,
  resourceButtonsPanel,
  ROSTER_DIALOG_ID,
  rosterPanel,
  storeItemsPanel,
  unitInfoPanel,
  type AtomFusionPanelView,
  type ResearchPanelView,
} from './state.ts';

/** The root's props. */
export interface RootProps {
  /** The server's answer. */
  world: WorldSnapshot;
  /** The content bundle. */
  bundle: ContentBundle;
  /** The item the player is about to place, or null. */
  placing?: number | null;
  /** The item the player selected on the map, or null. */
  selected?: number | null;
  /** The map id of the selected element, for its server attribute bag. */
  selectedIso?: number | null;
  /** The client's unix second, used only for on-screen countdowns. */
  now?: number;
  /** The player's time-zone offset in hours, for the local bonus day. */
  tzOffsetHours?: number;
  /** The other players, for the neighbour strip. */
  neighbours?: readonly Neighbour[];
  /** The tutorial step to draw, or null when the tutorial is not running. */
  tutorial?: TutorialOverlayProps | null;
  /** The one open dialog, or null when none is open. */
  dialog?: DialogState | null;
  /** The feedback messages read from the server's last answer. */
  feedback?: readonly FeedbackMessage[];
  /** The quest panel hosted by the shared dialog, or null. */
  questPanel?: QuestPanelView | null;
  /** True while a quest request is pending. */
  questBusy?: boolean;
  /** The player asked the dialog to close. */
  onDialogDismiss?: () => void;
  /** The player picked an opened chapter slot. */
  onQuestPick?: (choice: QuestChoice) => void;
  /** The player asked to start a quest at a difficulty, with an optional team. */
  onQuestStart?: (questId: string, difficulty: QuestDifficulty, team?: Army) => void;
  /** The player pressed one of the quest's allowed actions. */
  onQuestAction?: (questId: string, action: QuestActionChoice) => void;
  /** The player asked to retry (or replay) a finished mission. */
  onQuestRetry?: (questId: string) => void;
  /** The player asked to open the next mission the server made available. */
  onQuestNext?: (questId: string) => void;
  /** The player asked to collect the selected building's production. */
  onCollect?: () => void;
  /** The player picked a stored item to place on the map. */
  onPlaceStored?: (entry: StoredItemView) => void;
  /** The army the server's save accounts for, drawn beside storage. */
  army?: readonly ArmyUnitView[];
  /** The player asked for the daily bonus; the server decides the reward. */
  onClaimBonus?: () => void | Promise<unknown>;
  /** The player picked something to build, with its real wire type. */
  onPick?: (itemId: number, type: ItemType) => void;
  /** The player claimed a goal; send it through the client's transport. */
  onCommand?: (command: NativeCommand) => void;
  /** The player asked to upgrade the selected building. */
  onUpgrade?: () => void;
  /** The player asked to hurry the selected building's construction. */
  onFinish?: () => void;
  /** The player asked to train a unit in the selected building. */
  onTrain?: (unitItemId: number) => void;
  /** The player asked to take the finished unit out of the queue. */
  onTake?: () => void;
  /** The selected building's production cycle, when it can choose one. */
  production?: ProductionPanelView | null;
  /** The player asked to open the collection-period selector. */
  onOpenProduction?: () => void;
  /** The player picked one of the content's collection periods. */
  onActivate?: (period: number) => void;
}

/**
 * The interface.
 *
 * The HUD's state is derived from the world every time the world
 * changes, and the build menu's items are derived from the content
 * **once**: the content does not change while the game is running.
 */
export function Root({
  world,
  bundle,
  placing,
  selected,
  selectedIso = null,
  now = Math.floor(Date.now() / 1000),
  tzOffsetHours = 0,
  neighbours = [],
  tutorial = null,
  dialog = null,
  feedback = [],
  questPanel = null,
  questBusy = false,
  onDialogDismiss,
  onQuestPick,
  onQuestStart,
  onQuestAction,
  onQuestRetry,
  onQuestNext,
  onCollect,
  army = [],
  onPlaceStored,
  onClaimBonus,
  onPick,
  onCommand,
  onUpgrade,
  onFinish,
  onTrain,
  onTake,
  production = null,
  onOpenProduction,
  onActivate,
}: RootProps): React.JSX.Element {
  // The onboarding family and the chrome are UI-only state published by the
  // host; the panels they draw are readings of models, never decisions.
  const onboarding = useOnboarding();
  const chrome = useChrome();
  const roster = useRoster();
  const mystery = useMystery();
  const market = useMarket();
  const resourceButtons = useResourceButtons();
  const state = hudState(hudInput(bundle, world));
  const bonus = useMemo(
    () => bonusPanel(world, now, tzOffsetHours),
    [world, now, tzOffsetHours],
  );
  // The store front is a reading of the content's offer packs and the
  // server's cash. The bridge keeps no price or grant of its own: a missing
  // content row or wallet becomes an explicit empty state, and every buy
  // gesture is handed to the one command transport.
  const storeView = useMemo(() => storeItemsPanel(bundle, world), [bundle, world]);
  const items = useMemo(() => buildItems(bundle), [bundle]);
  const tabs = useMemo(() => categories(bundle), [bundle]);
  const placingName = useMemo(() => {
    if (placing === null || placing === undefined) return null;
    return items.find((item) => item.id === placing)?.name ?? null;
  }, [items, placing]);
  const goals = useMemo(() => goalList(bundle, world), [bundle, world]);
  // The neighbour count is the server's own list length, passed in when the
  // host has fetched it; without it no neighbour prompt is drawn.
  const expansion = useMemo(
    () => expansionPanel(bundle, world, neighbours.length),
    [bundle, world, neighbours],
  );
  const stored = useMemo(() => inventoryItems(bundle, world), [bundle, world]);
  const collections = useMemo(() => collectionsPanel(bundle, world), [bundle, world]);
  const ranks = useMemo(() => questRanks(world), [world]);
  const minLevels = useMemo(() => questMinLevels(bundle), [bundle]);
  // The chapter slots are gestures: a slot the server has opened can be
  // picked, and the active one can resume its authoritative panel.
  const activeQuestId = activeQuestState(world)?.questId ?? null;
  const choices = useMemo(
    () => questChoices(ranks, minLevels, levelOf(world), activeQuestId),
    [ranks, minLevels, world, activeQuestId],
  );
  const panel = useMemo(() => infoPanel(bundle, selected ?? null), [bundle, selected]);
  const unit = useMemo(() => unitInfoPanel(bundle, selected ?? null), [bundle, selected]);
  const building = useMemo(
    () => buildingInfo(bundle, world, selectedIso, now),
    [bundle, world, selectedIso, now],
  );
  const recruit = useMemo(
    () => recruitView(bundle, world, selectedIso, now),
    [bundle, world, selectedIso, now],
  );
  // The roster, the team thumbnails and the XP cards are one reading of the
  // same answer. The team is only passed in when the server bound one to the
  // active quest, so the strip never claims a team the server did not accept.
  const activeTeam = activeQuestState(world)?.team ?? null;
  const rosterView = useMemo(
    () => rosterPanel(bundle, world, now, activeTeam),
    [bundle, world, now, activeTeam],
  );

  // The market panel is a fresh reading of the server's counters and wallet.
  // It keeps no price, grant or trade outcome of its own; the launcher's open
  // flag is UI state and only decides which body the one dialog hosts.
  const marketView = useMemo(() => marketPanel(bundle, world), [bundle, world]);

  // The resource shortcut chrome is the same kind of reading: the wallet is
  // the server's, the content names and trade amounts are display text, and
  // the launcher's open flag is UI state that only selects a dialog body.
  const resourceButtonsView = useMemo(
    () => resourceButtonsPanel(bundle, world),
    [bundle, world],
  );

  // The extended portrait, the icon layout and the assault portraits are three
  // more readings of the server's save. The portrait is a unit the server
  // accounts for, the icons are its wallet's finite slots, and the assault
  // tiles use the same army and receipt the result dialog draws. None of them
  // owns a portrait, an amount or an outcome.
  const portraitView = useMemo(
    () => extendedPortraitPopup(bundle, world, now),
    [bundle, world, now],
  );
  const iconView = useMemo(() => resourceIconPanel(world), [world]);
  const assaultPortraitsView = useMemo(
    () => assaultPortraitPanel(bundle, world, now),
    [bundle, world, now],
  );
  // The launcher's open flag is UI state only; the body it hosts is the fresh
  // reading above and the one dialog's single slot is borrowed for it.
  const [portraitOpen, setPortraitOpen] = useState(false);
  // The Original art gallery is the same kind of UI-only gesture. It hosts a
  // fresh reading of the clean-room generator; it owns no game state and
  // borrows the one shared dialog rather than creating a second overlay.
  const [originalArtOpen, setOriginalArtOpen] = useState(false);
  // The Original FX panel is the same kind of UI-only gesture. Its animated
  // frames are a fresh reading of the clean-room generator; it owns no game
  // state and borrows the one shared dialog rather than creating an overlay.
  const [originalFxOpen, setOriginalFxOpen] = useState(false);

  // The one dialog's slot is shared. The market's, the resource chrome's, the
  // portrait launcher's and the art gallery's UI-only gestures borrow the same
  // primitive: when one is open it replaces the host's body for the moment and
  // is given back on close. No second overlay is ever created.
  const activeDialog: DialogState = originalFxOpen
    ? { dialog: originalFxDialog() }
    : originalArtOpen
      ? { dialog: originalArtDialog() }
      : portraitOpen
        ? { dialog: portraitDialog() }
        : resourceButtons.open
          ? { dialog: resourceButtonsDialog() }
          : market.open
            ? { dialog: marketDialog() }
            : (dialog ?? CLOSED_DIALOG);

  // The dialog's id selects which of the four assault-family screens to host.
  // Each view is a fresh reading of the server's answer: the interface keeps
  // no outcome, history row, strategy choice or charge of its own.
  const dialogId = activeDialog.dialog?.id ?? null;
  const assaultPanel = useMemo<AssaultPanelView | null>(() => {
    if (dialogId === 'assault-result') {
      const view = assaultResultPanel(bundle, world, now);
      return view ? { kind: 'result', view } : null;
    }
    if (dialogId === 'assault-history') {
      const view = assaultHistoryPanel(world, now);
      return view ? { kind: 'history', view: view.history, countdown: view.countdown } : null;
    }
    if (dialogId === 'assault-options') {
      return { kind: 'options', view: battleOptionsPanel(world) };
    }
    if (dialogId === 'assault-hud') {
      return { kind: 'hud', ...assaultHudPanel(world, now) };
    }
    return null;
  }, [dialogId, bundle, world, now]);

  // The last two modelled screen families are derived the same way: a fresh
  // reading of the server's save and the content for the hospital, and the
  // client's own literals plus the rules' damage classes for the symbol legend.
  // Neither keeps an outcome; each has only the one shared dialog's slot.
  const characterSetupPanel = useMemo<CharacterSetupPanelView | null>(() => {
    if (dialogId === 'charactersetup-hospital') {
      return { kind: 'hospital', view: hospitalPanel(bundle, world) };
    }
    if (dialogId === 'charactersetup-attack-symbols') {
      return { kind: 'attack-symbols', view: attackSymbolsPanel() };
    }
    return null;
  }, [dialogId, bundle, world]);

  // The Atom Fusion and research panels are fresh readings of the server's
  // save: the interface keeps no rolled power, granted item or countdown of
  // its own. The dialog id selects which body the one dialog hosts.
  const atomView = useMemo<AtomFusionPanelView | null>(
    () => (dialogId === 'fusion-atom' ? atomFusionPanel(bundle, world) : null),
    [dialogId, bundle, world],
  );
  const researchView = useMemo<ResearchPanelView | null>(() => {
    if (dialogId === 'research-area51') return researchPanel(bundle, world, 0, now);
    if (dialogId === 'research-robotic') return researchPanel(bundle, world, 1, now);
    return null;
  }, [dialogId, bundle, world, now]);

  return (
    <div className="swl-ui">
      <Hud state={state} placing={placingName} bonus={bonus} onClaimBonus={onClaimBonus} />
      <Goals goals={goals} onCommand={onCommand} />
      <Expansion view={expansion} onCommand={onCommand} />
      <Inventory
        items={stored}
        categories={tabs}
        collections={collections}
        army={army}
        onPlace={onPlaceStored}
      />
      <Chapters
        ranks={ranks}
        minLevels={minLevels}
        choices={choices}
        onQuestPick={onQuestPick}
      />
      <InfoPanel
        resource={panel}
        unit={unit}
        building={building}
        onCollect={onCollect}
        onUpgrade={onUpgrade}
        onFinish={onFinish}
        production={production}
        onOpenProduction={onOpenProduction}
      />
      <RecruitPanel view={recruit} onTrain={onTrain} onTake={onTake} />
      <Store view={storeView} onCommand={onCommand} />
      <MysteryLauncher bundle={bundle} />
      <SoulMixerLauncher />
      <FusionLauncher />
      <MagicLab bundle={bundle} world={world} onCommand={onCommand} />
      <SpellBook bundle={bundle} world={world} onCommand={onCommand} />
      <Neighbours neighbours={neighbours} />
      <OnboardingLauncher onOpen={onboarding.open ?? undefined} />
      <OriginalArtLauncher onOpen={() => setOriginalArtOpen(true)} />
      <OriginalFxLauncher onOpen={() => setOriginalFxOpen(true)} />
      {tutorial ? <TutorialOverlay {...tutorial} /> : null}
      <Feedback messages={feedback} />
      {/* The icon layout and the extended portrait launcher are presentations
          of the wallet and the army the server already published. */}
      <IconPanel view={iconView} />
      <ExtendedPortraitButton
        view={portraitView}
        onOpen={portraitView ? () => setPortraitOpen(true) : undefined}
      />
      <Dialog
        state={activeDialog}
        onDismiss={
          originalFxOpen
            ? () => setOriginalFxOpen(false)
            : originalArtOpen
              ? () => setOriginalArtOpen(false)
              : portraitOpen
                ? () => setPortraitOpen(false)
                : resourceButtons.open
                  ? closeResourceButtonsPanel
                  : market.open
                    ? closeMarketPanel
                    : onDialogDismiss ?? (() => {})
        }
      >
        {originalFxOpen || originalArtOpen || (!market.open && !resourceButtons.open) ? (
        <>
        {originalFxOpen ? (
          <OriginalFxGallery onClose={() => setOriginalFxOpen(false)} />
        ) : null}
        {originalArtOpen ? (
          <OriginalArtGallery onClose={() => setOriginalArtOpen(false)} />
        ) : null}
        {!onboarding.view && !dialogId?.startsWith('assault-') && !dialogId?.startsWith('charactersetup-') && !dialogId?.startsWith('mystery-') && !dialogId?.startsWith('soulmixer-') && !dialogId?.startsWith('fusion-') && !dialogId?.startsWith('research-') && dialogId !== ROSTER_DIALOG_ID && dialogId !== PORTRAIT_DIALOG_ID && dialogId !== ORIGINAL_FX_DIALOG_ID && questPanel && onQuestStart && onQuestAction ? (
          <QuestPanel
            key={
              questPanel.kind === 'briefing'
                ? `briefing:${questPanel.briefing.questId}`
                : questPanel.kind === 'combat'
                  ? `combat:${questPanel.active.questId}`
                  : `result:${questPanel.result.kind}`
            }
            view={questPanel}
            busy={questBusy}
            onStart={onQuestStart}
            onAction={onQuestAction}
            onRetry={onQuestRetry}
            onNext={onQuestNext}
            onCancel={onDialogDismiss ?? (() => {})}
          />
        ) : null}
        {!onboarding.view && dialogId === ROSTER_DIALOG_ID && rosterView ? (
          <RosterPanel
            key="roster-army"
            view={rosterView}
            onSubmit={roster.submitTeam ?? undefined}
            onCancel={onDialogDismiss ?? (() => {})}
          />
        ) : null}
        {!onboarding.view && dialog?.dialog?.id === PRODUCTION_DIALOG_ID && production && onActivate ? (
          <ProductionSelector view={production} onActivate={onActivate} />
        ) : null}
        {!onboarding.view && assaultPanel ? (
          <>
            {dialogId === 'assault-result' ? (
              <AssaultPortraits view={assaultPortraitsView} />
            ) : null}
            <AssaultPanel
              key={dialogId ?? undefined}
              panel={assaultPanel}
              // The one transport is a request, not a local decision: the host
              // redraws from the server's answer, so no pending assault state is
              // held here to disable the buttons.
              busy={false}
              onCommand={onCommand}
              onCancel={onDialogDismiss ?? (() => {})}
            />
          </>
        ) : null}
        {!onboarding.view && characterSetupPanel ? (
          <CharacterSetupPanel
            key={`charactersetup:${characterSetupPanel.kind}`}
            panel={characterSetupPanel}
            onCommand={onCommand}
            onCancel={onDialogDismiss ?? (() => {})}
          />
        ) : null}
        {!onboarding.view && dialogId?.startsWith('mystery-') ? (
          <MysteryPanel
            key={`mystery:${dialogId}`}
            view={mystery.view}
            result={mystery.result}
            onClose={onDialogDismiss ?? (() => {})}
          />
        ) : null}
        {!onboarding.view && dialogId?.startsWith('soulmixer-') ? (
          <SoulMixerPanel
            key={`soulmixer:${dialogId}`}
            world={world}
            onClose={onDialogDismiss ?? (() => {})}
          />
        ) : null}
        {!onboarding.view && atomView ? (
          <AtomFusionPanel
            key={`fusion:${dialogId}`}
            view={atomView}
            onCommand={onCommand}
            onClose={onDialogDismiss ?? (() => {})}
          />
        ) : null}
        {!onboarding.view && researchView ? (
          <ResearchPanel
            key={`research:${dialogId}`}
            view={researchView}
            onCommand={onCommand}
            onClose={onDialogDismiss ?? (() => {})}
          />
        ) : null}
        {!onboarding.view && dialogId === PORTRAIT_DIALOG_ID ? (
          <PortraitPopupBody
            key={`portrait:${portraitView?.itemId ?? 'empty'}`}
            view={portraitView}
            onClose={() => setPortraitOpen(false)}
          />
        ) : null}
        {onboarding.view ? (
          <OnboardingPanel
            key={`onboarding:${onboarding.view.kind}:${dialogId ?? ''}`}
            view={onboarding.view}
            onCancel={onDialogDismiss ?? (() => {})}
            onStart={onboarding.start ?? undefined}
            onNext={onboarding.next ?? undefined}
            onSkip={onboarding.skip ?? undefined}
            onConfirm={onboarding.confirm ?? undefined}
          />
        ) : null}
        {chrome.popup && dialogId === chrome.popup.id ? (
          <ChromePopupBody
            key={`chrome:${chrome.popup.id}`}
            request={chrome.popup}
            onAcknowledge={chrome.dismissNotice ?? undefined}
          />
        ) : null}
        </>
        ) : null}
        {market.open ? (
          <MarketPanel
            key="market-player-owned"
            view={marketView}
            onCommand={onCommand}
            onClose={closeMarketPanel}
          />
        ) : null}
        {resourceButtons.open ? (
          <ResourceButtonsPanel
            key="resource-buttons-chrome"
            view={resourceButtonsView}
            onCommand={onCommand}
            onClose={closeResourceButtonsPanel}
          />
        ) : null}
      </Dialog>
      <ChromeDock
        world={world}
        bundle={bundle}
        categories={tabs}
        items={items}
        playerLevel={state.level}
        feedback={feedback}
        building={building}
        production={production}
        selectedIso={selectedIso}
        onCollect={onCollect}
        onFinish={onFinish}
        onPick={onPick ? (entryId, type) => onPick(entryId, type) : undefined}
      />
      <BuildMenu
        items={items}
        categories={tabs}
        playerLevel={state.level}
        onPick={onPick ? (entry) => onPick(entry.id, entry.type) : undefined}
      />
    </div>
  );
}
