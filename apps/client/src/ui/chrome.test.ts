import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  MAX_ZOOM,
  MIN_ZOOM,
  tileToPixel,
  viewportOf,
  type BuildMenuItem,
  type BuildingInfoView,
  type CameraState,
  type WorldSnapshot,
} from '@swl/client';
import type { ContentBundle, ContentItem } from '@swl/content';

import { uiCss } from './css.ts';
import {
  EMPTY_POPUP_SLOT,
  EMPTY_TAB_STRIP,
  NO_ATTACHMENT,
  NO_NOTICES,
  acknowledgeNotice,
  attachTo,
  attachmentPixel,
  chromeActions,
  chromeAttachment,
  chromeBuildTabs,
  chromeCatalogue,
  chromePopupDialog,
  dettach,
  dismissPopup,
  isAttachedTo,
  noticeVisible,
  requestPopup,
  speakerNotice,
  tabStrip,
  tabViews,
  zoomFromPercent,
  zoomView,
  type ProductionPanelView,
} from './state.ts';

const camera = (zoom = 1): CameraState => ({ topX: 10, topY: 20, zoom });

const categories = {
  1: { id: 1, name: 'Houses and resources', sub: [{ id: 11, name: 'Houses' }] },
  2: { id: 2, name: 'Defenses', sub: [{ id: 21, name: 'Towers' }] },
};

function item(overrides: Partial<BuildMenuItem> = {}): BuildMenuItem {
  return {
    id: 1,
    type: 'b',
    name: 'House I',
    categoryId: 1,
    subcategoryId: 11,
    displayOrder: 10,
    minLevel: 1,
    costs: { w: 30 },
    buildTime: 5,
    clicksToBuild: 1,
    inStore: true,
    ...overrides,
  };
}

function bundle(): ContentBundle {
  return {
    items: [{ id: 7, name: 'Marine' } as ContentItem],
    levels: [],
    globals: {},
    categories,
    questEvents: {},
  } as unknown as ContentBundle;
}

function world(): WorldSnapshot {
  return {
    maps: [{ id: 0, items: { 11: [7, 4, 9, 0, 0, 0, {}] } }],
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
    privateState: {},
  } as unknown as WorldSnapshot;
}

describe('the chrome tab and sub-category pill state', () => {
  it('replaces the one selection and one hover slot', () => {
    const picked = tabStrip(EMPTY_TAB_STRIP, { type: 'select', id: 'cat:1' });
    assert.equal(picked.selectedId, 'cat:1');
    assert.equal(picked.hoveredId, null);
    const hovered = tabStrip(picked, { type: 'hover', id: 'cat:2' });
    assert.equal(hovered.selectedId, 'cat:1', 'hover does not change the selection');
    assert.equal(hovered.hoveredId, 'cat:2');
    assert.equal(
      tabStrip(hovered, { type: 'hover', id: null }).hoveredId,
      null,
      'outPastilla clears the hover',
    );
    assert.equal(tabStrip(picked, { type: 'select', id: 'cat:2' }).selectedId, 'cat:2');
    assert.equal(tabStrip(picked, { type: 'select', id: 'cat:1' }), picked, 'no new state');
  });

  it('marks exactly one tab selected and one hovered for drawing', () => {
    const state = tabStrip(
      tabStrip(EMPTY_TAB_STRIP, { type: 'select', id: 'sub:11' }),
      { type: 'hover', id: 'sub:11' },
    );
    const views = tabViews(
      [{ id: 'sub:11', label: 'Houses' }, { id: 'sub:21', label: 'Towers' }],
      state,
    );
    assert.deepEqual(views[0], {
      id: 'sub:11', label: 'Houses', selected: true, hovered: true,
    });
    assert.deepEqual(views[1], {
      id: 'sub:21', label: 'Towers', selected: false, hovered: false,
    });
  });

  it('derives tabs and sub-categories from the content and filters its entries', () => {
    const tabs = chromeBuildTabs(categories);
    assert.deepEqual(tabs.map((tab) => tab.id), ['cat:1', 'cat:2']);
    assert.deepEqual(tabs[0]!.subs, [{ id: 'sub:11', label: 'Houses' }]);
    const items = [
      item({ id: 1, categoryId: 1, subcategoryId: 11 }),
      item({ id: 2, categoryId: 1, subcategoryId: 12 }),
      item({ id: 3, categoryId: 2, subcategoryId: 21 }),
    ];
    assert.deepEqual(
      chromeCatalogue(items, 'cat:1', null).map((entry) => entry.id),
      [1, 2],
    );
    assert.deepEqual(
      chromeCatalogue(items, 'cat:1', 'sub:11').map((entry) => entry.id),
      [1],
    );
    assert.deepEqual(chromeCatalogue(items, null, null), []);
  });
});

describe('the zoom slider bound to the camera model', () => {
  it('reads the camera and exposes the camera module bounds', () => {
    const view = zoomView(camera(0.5));
    assert.equal(view.zoom, 0.5);
    assert.equal(view.percent, 50);
    assert.equal(view.minPercent, Math.round(MIN_ZOOM * 100));
    assert.equal(view.maxPercent, Math.round(MAX_ZOOM * 100));
    assert.equal(view.canZoomIn, true);
    assert.equal(view.canZoomOut, true);
    assert.equal(view.label, 'Zoom 50%');
  });

  it('disables the step at the bounds without moving past them', () => {
    assert.equal(zoomView(camera(MAX_ZOOM)).canZoomIn, false);
    assert.equal(zoomView(camera(MIN_ZOOM)).canZoomOut, false);
    assert.equal(zoomView(camera(Number.NaN)).zoom, 1, 'a broken camera zoom falls back');
  });

  it('turns a percent into a camera zoom, clamped, keeping the pan', () => {
    assert.equal(zoomFromPercent(camera(), 75).zoom, 0.75);
    assert.equal(zoomFromPercent(camera(), 10).zoom, MIN_ZOOM);
    assert.equal(zoomFromPercent(camera(), 999).zoom, MAX_ZOOM);
    assert.equal(zoomFromPercent(camera(), Number.NaN).zoom, 1);
    const moved = zoomFromPercent(camera(), 75);
    assert.equal(moved.topX, 10);
    assert.equal(moved.topY, 20);
  });
});

describe('the speaker box acknowledgement', () => {
  it('reads only the server answer the host published', () => {
    assert.equal(
      speakerNotice([
        { tone: 'success', text: 'Command 4 succeeded.' },
        { tone: 'error', text: 'Command 5 was refused.' },
      ])?.text,
      'Command 5 was refused.',
    );
    assert.equal(speakerNotice([]), null);
    assert.equal(speakerNotice([{ tone: 'success', text: '' }]), null);
  });

  it('records the OK by notice id and never changes the world', () => {
    const notice = speakerNotice([{ tone: 'error', text: 'No such building.' }])!;
    assert.equal(noticeVisible(notice, NO_NOTICES), true);
    const acked = acknowledgeNotice(NO_NOTICES, notice.id);
    assert.equal(noticeVisible(notice, acked), false);
    assert.equal(acknowledgeNotice(acked, notice.id), acked, 'a second OK is a no-op');
    assert.equal(NO_NOTICES.acknowledged.length, 0, 'the shared empty state is not mutated');
  });
});

describe('the collect and hurry-up affordances', () => {
  const production = (due: boolean) => ({
    isoId: 11, name: 'Depot', resource: 'g', period: 1, startedAt: 0,
    secondsRemaining: due ? 0 : 30, due, options: [],
  }) as ProductionPanelView;
  const finished = (): BuildingInfoView => ({
    name: 'House I', upgrade: null, finish: { remainingSeconds: 12, clicksToBuild: 3 },
  });
  const idle = (): BuildingInfoView => ({ name: 'House I', upgrade: null, finish: null });

  it('enables collect only when the server says the cycle is due', () => {
    const [collect] = chromeActions(idle(), production(true))!;
    assert.equal(collect!.kind, 'collect');
    assert.equal(collect!.enabled, true);
    assert.equal(collect!.note, 'Ready');
    assert.equal(chromeActions(idle(), production(false))![0]!.enabled, false);
    assert.equal(chromeActions(idle(), null)![0]!.enabled, false);
  });

  it('enables hurry only while the server says a build is in progress', () => {
    const [collect, hurry] = chromeActions(finished(), production(false))!;
    assert.equal(collect!.enabled, false);
    assert.equal(hurry!.kind, 'hurry');
    assert.equal(hurry!.enabled, true);
    assert.equal(hurry!.note, '12s · 3 clicks');
    assert.equal(chromeActions(idle(), null)![1]!.enabled, false);
  });
});

describe('world-space attachables', () => {
  it('anchors to a tile the server actually published', () => {
    const target = chromeAttachment(bundle(), world(), 11)!;
    assert.deepEqual(target, { isoId: 11, itemId: 7, name: 'Marine', tx: 4, ty: 9 });
    assert.equal(chromeAttachment(bundle(), world(), null), null);
    assert.equal(chromeAttachment(bundle(), world(), 99), null);
  });

  it('has one attached slot with an attach/dettach lifecycle', () => {
    const a = chromeAttachment(bundle(), world(), 11)!;
    const attached = attachTo(NO_ATTACHMENT, a);
    assert.equal(isAttachedTo(attached, a), true);
    assert.equal(isAttachedTo(NO_ATTACHMENT, a), false);
    assert.equal(isAttachedTo(attached, null), false);
    assert.equal(isAttachedTo(dettach(attached), a), false);
    assert.equal(dettach(NO_ATTACHMENT), NO_ATTACHMENT);
  });

  it('projects through the client camera, never a second projection', () => {
    const a = chromeAttachment(bundle(), world(), 11)!;
    const cam = camera(1);
    assert.deepEqual(
      attachmentPixel(a, cam),
      tileToPixel(a.tx, a.ty, viewportOf(cam)),
    );
  });
});

describe('the one-slot popup queue', () => {
  const request = (id: string, priority: number) => ({
    id, priority, title: id, message: `Notice ${id}`,
  });

  it('opens the first request and waits the rest by priority', () => {
    const first = requestPopup(EMPTY_POPUP_SLOT, request('low', 1));
    assert.equal(first.open?.id, 'low');
    const queued = requestPopup(requestPopup(first, request('urgent', 9)), request('mid', 5));
    assert.equal(queued.open?.id, 'low', 'no second modal opens');
    assert.deepEqual(queued.pending.map((entry) => entry.id), ['urgent', 'mid']);
    assert.deepEqual(dismissPopup(queued).open, request('urgent', 9));
    assert.deepEqual(dismissPopup(dismissPopup(queued)).open, request('mid', 5));
    assert.equal(dismissPopup(dismissPopup(dismissPopup(queued))).open, null);
  });

  it('keeps request order when priorities tie and hosts the body in one dialog', () => {
    const opened = requestPopup(EMPTY_POPUP_SLOT, request('first', 1));
    const slot = requestPopup(requestPopup(opened, request('a', 1)), request('b', 1));
    assert.equal(slot.open?.id, 'first');
    assert.deepEqual(slot.pending.map((entry) => entry.id), ['a', 'b']);
    assert.deepEqual(chromePopupDialog(request('chrome-notice', 1)), {
      id: 'chrome-notice', kind: 'alert', title: 'chrome-notice',
    });
  });
});

describe('the chrome stylesheet', () => {
  it('draws every primitive with its own class', () => {
    const css = uiCss();
    for (const className of [
      'swl-chrome-tabs', 'swl-chrome-pills', 'swl-chrome-tab-selected',
      'swl-chrome-tab-hover', 'swl-chrome-popover', 'swl-chrome-cover',
      'swl-chrome-zoom-range', 'swl-chrome-speaker', 'swl-chrome-action-hurry',
      'swl-chrome-action-collect', 'swl-chrome-attachable', 'swl-chrome-popup',
    ]) {
      assert.ok(css.includes(`.${className}`), `${className} has no stylesheet rule`);
    }
  });
});
