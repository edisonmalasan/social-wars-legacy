/**
 * The reusable UI-chrome family.
 *
 * This is the drawing of the primitives whose behaviour is modelled in
 * `state.ts`: tab strips and sub-category pills, a popover with a cover,
 * the zoom slider bound to the camera model, a speaker box with an OK
 * acknowledgement, collect/hurry-up affordances that only send requests,
 * a world-space attachable, and the priority queue for the **one** dialog.
 *
 * Nothing here is a second authority. The tabs and hover marks are UI state;
 * the zoom is the camera the renderer really uses; the attachments are
 * anchored to tiles the server actually published; and every game gesture
 * calls a host callback that sends a request and redraws from the answer.
 * The popup queue only chooses which body the shared `dialog.tsx` hosts — it
 * never opens another modal. The original's proprietary art is excluded:
 * the chrome is drawn with text, CSS and the client's own glyphs.
 */
import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react';

import {
  initialCamera,
  type BuildMenuItem,
  type BuildingInfoView,
  type CameraState,
  type FeedbackMessage,
  type ItemType,
  type WorldSnapshot,
} from '@swl/client';
import type { ContentBundle } from '@swl/content';

import {
  acknowledgeNotice,
  attachTo,
  attachmentPixel,
  chromeActions,
  chromeAttachment,
  chromeBuildTabs,
  chromeCatalogue,
  dettach,
  isAttachedTo,
  NO_ATTACHMENT,
  NO_NOTICES,
  noticeVisible,
  speakerNotice,
  tabStrip,
  tabViews,
  zoomFromPercent,
  zoomView,
  type AttachmentState,
  type ChromePopupRequest,
  type NoticeState,
  type TabStripAction,
  type TabStripState,
} from './state.ts';
import { EMPTY_TAB_STRIP } from './state.ts';
import type { Categories, ProductionPanelView } from './state.ts';
import { MarketLauncher } from './market.tsx';
import { ResourceButtonsLauncher } from './resourcebuttons.tsx';

/** The host callbacks the chrome needs. `main.ts` publishes them once. */
export interface ChromeHost {
  /** The camera the renderer is actually drawing, for zoom and attachments. */
  readonly camera: CameraState | null;
  /** Apply the camera model's slider step in each direction. */
  readonly zoomIn: (() => void) | null;
  readonly zoomOut: (() => void) | null;
  /** Move the slider to an integer percent of the camera's range. */
  readonly zoomTo: ((percent: number) => void) | null;
  /** Queue the server's latest notice as a popup in the one dialog. */
  readonly openNotice: (() => void) | null;
  /** Dismiss the open chrome popup and promote the next one. */
  readonly dismissNotice: (() => void) | null;
  /** The popup the one dialog is currently hosting, for its body. */
  readonly popup: ChromePopupRequest | null;
}

const CLOSED_HOST: ChromeHost = {
  camera: null,
  zoomIn: null,
  zoomOut: null,
  zoomTo: null,
  openNotice: null,
  dismissNotice: null,
  popup: null,
};

let host: ChromeHost = CLOSED_HOST;
const listeners = new Set<() => void>();

/** Publish or patch the host's UI-only gestures and camera reading. */
export function setChromeHost(patch: Partial<ChromeHost>): void {
  host = { ...host, ...patch };
  for (const listener of listeners) listener();
}

/** The current chrome host, for tests and for the view. */
export function chromeHost(): ChromeHost {
  return host;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Read the chrome host from a component. */
export function useChrome(): ChromeHost {
  return useSyncExternalStore(subscribe, chromeHost, chromeHost);
}

/** A row of tabs or pills. Selection and hover are the only state it owns. */
export function ChromeTabStrip({
  entries,
  state,
  onAction,
  className,
  ariaLabel,
  controls,
}: {
  readonly entries: readonly { readonly id: string; readonly label: string }[];
  readonly state: TabStripState;
  readonly onAction: (action: TabStripAction) => void;
  readonly className: string;
  readonly ariaLabel: string;
  readonly controls?: string;
}): React.JSX.Element {
  const views = tabViews(entries, state);
  return (
    <div className={className} role="tablist" aria-label={ariaLabel}>
      {views.map((view) => (
        <button
          key={view.id}
          type="button"
          role="tab"
          aria-selected={view.selected}
          aria-controls={controls}
          className={
            view.selected
              ? `swl-chrome-tab swl-chrome-tab-selected${view.hovered ? ' swl-chrome-tab-hover' : ''}`
              : `swl-chrome-tab${view.hovered ? ' swl-chrome-tab-hover' : ''}`
          }
          onMouseEnter={() => onAction({ type: 'hover', id: view.id })}
          onMouseLeave={() => onAction({ type: 'hover', id: null })}
          onFocus={() => onAction({ type: 'hover', id: view.id })}
          onBlur={() => onAction({ type: 'hover', id: null })}
          onClick={() => onAction({ type: 'select', id: view.id })}
        >
          {view.label}
        </button>
      ))}
    </div>
  );
}

/**
 * The dimming, click-to-dismiss layer.
 *
 * The shared dialog keeps its own backdrop; this primitive is the same idea
 * for the chrome's non-modal popover, so a dismissal has one shape whether
 * the player clicks a cover, presses Escape or uses a button.
 */
export function Cover({
  onDismiss,
  className = 'swl-chrome-cover',
}: {
  readonly onDismiss: () => void;
  readonly className?: string;
}): React.JSX.Element {
  return (
    <div
      className={className}
      aria-hidden="true"
      onClick={onDismiss}
    />
  );
}

/** The chrome panel drawn over the stage. */
export function ChromeDock({
  world,
  bundle,
  categories,
  items,
  playerLevel,
  feedback,
  building,
  production,
  selectedIso,
  onCollect,
  onFinish,
  onPick,
}: {
  readonly world: WorldSnapshot;
  readonly bundle: ContentBundle;
  readonly categories: Categories;
  readonly items: readonly BuildMenuItem[];
  readonly playerLevel: number;
  readonly feedback: readonly FeedbackMessage[];
  readonly building: BuildingInfoView | null;
  readonly production: ProductionPanelView | null;
  readonly selectedIso: number | null;
  readonly onCollect?: () => void;
  readonly onFinish?: () => void;
  readonly onPick?: (itemId: number, type: ItemType) => void;
}): React.JSX.Element {
  const chrome = useChrome();
  const [strip, setStrip] = useState<TabStripState>(EMPTY_TAB_STRIP);
  const [pills, setPills] = useState<TabStripState>(EMPTY_TAB_STRIP);
  const [acks, setAcks] = useState<NoticeState>(NO_NOTICES);
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [attachment, setAttachment] = useState<AttachmentState>(NO_ATTACHMENT);
  const popover = useRef<HTMLDivElement>(null);
  const helpButton = useRef<HTMLButtonElement>(null);

  const tabs = useMemo(() => chromeBuildTabs(categories), [categories]);
  const active = tabs.find((tab) => tab.id === strip.selectedId) ?? null;
  const catalogue = useMemo(
    () => chromeCatalogue(items, strip.selectedId, pills.selectedId),
    [items, strip.selectedId, pills.selectedId],
  );
  const camera = chrome.camera ?? initialCamera();
  const zoom = zoomView(camera);
  const actions = chromeActions(building, production);
  const notice = speakerNotice(feedback);
  const target = useMemo(
    () => chromeAttachment(bundle, world, selectedIso),
    [bundle, world, selectedIso],
  );

  // The attach/dettach lifecycle follows the server's selection, not a timer.
  useEffect(() => {
    setAttachment((current) =>
      target
        ? isAttachedTo(current, target)
          ? current
          : attachTo(current, target)
        : dettach(current),
    );
  }, [target]);

  // Escape is the popover's other dismissal; focus comes back to its button.
  useEffect(() => {
    if (!popoverOpen) return;
    popover.current?.focus();
    function onKey(event: KeyboardEvent): void {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      setPopoverOpen(false);
      helpButton.current?.focus();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [popoverOpen]);

  return (
    <div className="swl-chrome" aria-label="Interface controls">
      {popoverOpen ? (
        <Cover onDismiss={() => setPopoverOpen(false)} />
      ) : null}
      <div className="swl-chrome-head">
        <span className="swl-chrome-title">Controls</span>
        <div className="swl-chrome-head-actions">
          {/*
            The market gesture lives here, with the other chrome controls. It
            only publishes a UI-only open flag; the panel is hosted by the one
            shared dialog in `root.tsx` and every trade goes through the host's
            one command transport.
          */}
          <MarketLauncher />
          {/*
            The resource-shortcut/chrome gesture lives here with the other
            interface controls. Like the market's, it only publishes a UI-only
            open flag; the panel is hosted by the one shared dialog in
            `root.tsx` and every trade goes through the host's one transport.
          */}
          <ResourceButtonsLauncher />
          <button
            ref={helpButton}
            type="button"
            className="swl-chrome-help"
            aria-label="About these controls"
            aria-expanded={popoverOpen}
            aria-controls="swl-chrome-popover"
            onClick={() => setPopoverOpen((open) => !open)}
          >
            ?
          </button>
        </div>
      </div>
      {popoverOpen ? (
        <div
          ref={popover}
          id="swl-chrome-popover"
          className="swl-chrome-popover"
          role="tooltip"
          tabIndex={-1}
        >
          <p className="swl-chrome-popover-line">
            {zoom.label}. The slider moves the same camera the map draws.
          </p>
          <p className="swl-chrome-popover-line">
            Collect and Hurry up only ask the server; its answer redraws the world.
          </p>
          <button
            type="button"
            className="swl-chrome-popover-ok"
            onClick={() => {
              setPopoverOpen(false);
              helpButton.current?.focus();
            }}
          >
            Got it
          </button>
        </div>
      ) : null}

      <div className="swl-chrome-zoom" role="group" aria-label="Map zoom">
        <button
          type="button"
          className="swl-chrome-zoom-step"
          aria-label="Zoom out"
          disabled={!zoom.canZoomOut || chrome.zoomOut === null}
          onClick={() => chrome.zoomOut?.()}
        >
          −
        </button>
        <input
          type="range"
          className="swl-chrome-zoom-range"
          aria-label="Zoom"
          min={zoom.minPercent}
          max={zoom.maxPercent}
          step={1}
          value={zoom.percent}
          disabled={chrome.zoomTo === null}
          onChange={(event) => chrome.zoomTo?.(Number(event.currentTarget.value))}
        />
        <button
          type="button"
          className="swl-chrome-zoom-step"
          aria-label="Zoom in"
          disabled={!zoom.canZoomIn || chrome.zoomIn === null}
          onClick={() => chrome.zoomIn?.()}
        >
          +
        </button>
        <span className="swl-chrome-zoom-value">{zoom.label}</span>
      </div>

      <div className="swl-chrome-actions">
        {actions.map((action) => (
          <button
            key={action.kind}
            type="button"
            className={`swl-chrome-action swl-chrome-action-${action.kind}`}
            disabled={
              !action.enabled ||
              (action.kind === 'collect' ? !onCollect : !onFinish)
            }
            onClick={() => (action.kind === 'collect' ? onCollect?.() : onFinish?.())}
          >
            <span className="swl-chrome-action-mark" aria-hidden="true">
              {action.kind === 'collect' ? '↧' : '»'}
            </span>
            <span className="swl-chrome-action-label">{action.label}</span>
            <span className="swl-chrome-action-note">{action.note}</span>
          </button>
        ))}
      </div>

      {notice ? (
        <div className="swl-chrome-notice">
          <button
            type="button"
            className="swl-chrome-notice-open"
            disabled={!chrome.openNotice}
            onClick={() => chrome.openNotice?.()}
          >
            Notice
          </button>
          {noticeVisible(notice, acks) ? (
            <div className="swl-chrome-speaker" role="status">
              <span className="swl-chrome-speaker-mark" aria-hidden="true">!</span>
              <span className="swl-chrome-speaker-text">{notice.text}</span>
              <button
                type="button"
                className="swl-chrome-speaker-ok"
                onClick={() =>
                  setAcks((current) => acknowledgeNotice(current, notice.id))
                }
              >
                OK
              </button>
            </div>
          ) : null}
        </div>
      ) : null}

      <ChromeTabStrip
        entries={tabs}
        state={strip}
        onAction={(action) => {
          setStrip((current) => tabStrip(current, action));
          setPills(EMPTY_TAB_STRIP);
        }}
        className="swl-chrome-tabs"
        ariaLabel="Build categories"
        controls="swl-chrome-catalogue"
      />
      {active ? (
        <ChromeTabStrip
          entries={active.subs}
          state={pills}
          onAction={(action) => setPills((current) => tabStrip(current, action))}
          className="swl-chrome-pills"
          ariaLabel="Sub-categories"
          controls="swl-chrome-catalogue"
        />
      ) : null}
      <ul
        id="swl-chrome-catalogue"
        className="swl-chrome-catalogue"
        role="tabpanel"
        aria-label="Content entries"
      >
        {catalogue.map((entry) => (
          <li key={`${entry.type}:${entry.id}`}>
            <button
              type="button"
              className="swl-chrome-catalogue-item"
              onClick={() => onPick?.(entry.id, entry.type)}
            >
              {entry.name}
            </button>
          </li>
        ))}
      </ul>

      {target && isAttachedTo(attachment, target) ? (
        <div
          className="swl-chrome-attachable"
          data-swl-attached={target.isoId}
          style={(() => {
            const pixel = attachmentPixel(target, camera);
            return { left: pixel.x, top: pixel.y };
          })()}
          aria-hidden="true"
        >
          <span className="swl-chrome-attach-arrow">▼</span>
          <span className="swl-chrome-attach-label">{target.name}</span>
        </div>
      ) : null}
    </div>
  );
}

/** The body the one shared dialog hosts for a chrome popup. */
export function ChromePopupBody({
  request,
  onAcknowledge,
}: {
  readonly request: ChromePopupRequest | null;
  readonly onAcknowledge?: () => void;
}): React.JSX.Element | null {
  if (!request) return null;
  return (
    <div className="swl-chrome-popup" role="status">
      <p className="swl-chrome-popup-message">{request.message}</p>
      <div className="swl-chrome-popup-actions">
        <button type="button" className="swl-chrome-popup-ok" onClick={onAcknowledge}>
          OK
        </button>
      </div>
    </div>
  );
}
