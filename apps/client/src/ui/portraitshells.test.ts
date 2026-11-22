/**
 * Tests for the extended portrait popup, icon panel and assault portraits.
 *
 * The art module is JSX-free so Node's native TypeScript stripper can load it;
 * a small `registerHooks` loader renders the real components with
 * `react-dom/server`. Every assertion checks that the panel draws only what
 * the server published, and that the art is original and inert.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { registerHooks, stripTypeScriptTypes } from 'node:module';
import { fileURLToPath } from 'node:url';

import * as React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

import type { WorldSnapshot } from '@swl/client';
import type { ContentBundle, ContentItem } from '@swl/content';

import {
  assaultPortraitPanel,
  extendedPortraitPopup,
  resourceIconPanel,
} from './state.ts';
import type {
  AssaultPortraitPanelView,
  ExtendedPortraitPopupView,
  IconPanelView,
} from './state.ts';

registerHooks({
  load(url, context, nextLoad) {
    if (url.endsWith('portraitshells.tsx')) {
      const source = readFileSync(fileURLToPath(url), 'utf8');
      return { format: 'module', shortCircuit: true, source: stripTypeScriptTypes(source) };
    }
    return nextLoad(url, context);
  },
});

const art = await import('./portraitshells.tsx');

function bundle(): ContentBundle {
  return {
    items: [
      {
        id: 7,
        name: 'Marine',
        type: 'u',
        group_type: 'infantry',
        training_time: 5,
        life: 100,
      } as ContentItem,
      {
        id: 8,
        name: 'Archer',
        type: 'u',
        group_type: 'ranged',
        training_time: 7,
        life: 50,
      } as ContentItem,
    ],
    levels: [],
    globals: {
      UNIT_XP_LEVELS_MULTIPLIERS_10: [
        [0, 0, 0, 0],
        [5, 2, 20, 50],
        [10, 2, 20, 25],
      ],
    },
    categories: {},
    questEvents: {},
  } as unknown as ContentBundle;
}

function world(patch: Record<string, unknown> = {}): WorldSnapshot {
  return {
    maps: [{ id: 0, store: { 7: 3 }, items: {} }],
    resources: { e: 12, x: 40, g: 500, w: 25, o: 8, s: 4, c: 10, m: 2 },
    privateState: {
      lastAssaultWon: true,
      lastAssaultResult: { won: true, rewards: [], opponent: 'village-9' },
    },
    ...patch,
  } as unknown as WorldSnapshot;
}

const renderButton = (view: ExtendedPortraitPopupView | null): string =>
  renderToStaticMarkup(React.createElement(art.ExtendedPortraitButton, { view, onOpen: () => {} }));
const renderIcons = (view: IconPanelView): string =>
  renderToStaticMarkup(React.createElement(art.IconPanel, { view }));
const renderAssault = (view: AssaultPortraitPanelView): string =>
  renderToStaticMarkup(React.createElement(art.AssaultPortraits, { view }));

describe('the extended portrait popup reads only the server army', () => {
  it('names the server unit, count and rules level', () => {
    const view = extendedPortraitPopup(bundle(), world(), 0);
    assert.deepEqual(view, { itemId: 7, name: 'Marine', count: 3, level: 0 });
    const markup = renderButton(view);
    assert.match(markup, /data-swl-portrait-popup="open"/);
    assert.ok(markup.includes('data-swl-unit-id="7"'), 'the server item id is drawn');
    assert.ok(markup.includes('data-swl-portrait-count="3"'), 'the server count is drawn');
    assert.ok(markup.includes('Marine'), 'the content name is drawn');
  });

  it('has no portrait, name or count when the server owns no unit', () => {
    for (const w of [world({ maps: [{ id: 0, store: {}, items: {} }] }), world({ maps: [] })]) {
      assert.equal(extendedPortraitPopup(bundle(), w, 0), null);
      const markup = renderButton(null);
      assert.match(markup, /data-swl-portrait-popup="empty"/);
      assert.ok(markup.includes(art.NO_PORTRAIT_CAPTION));
      assert.ok(!markup.includes('data-swl-unit-id='), 'no id is invented');
      assert.ok(!markup.includes('data-swl-portrait-count='), 'no count is invented');
      assert.ok(!markup.includes('Marine'), 'no name is invented');
    }
  });

  it('opens the one shared dialog with its own id', () => {
    assert.deepEqual(art.portraitDialog(), {
      id: art.PORTRAIT_DIALOG_ID,
      kind: 'alert',
      title: 'Unit portrait',
    });
  });
});

describe('the icon panel reads only the server wallet', () => {
  it('draws one icon per finite wallet slot, in wire order', () => {
    const view = resourceIconPanel(world());
    assert.deepEqual(
      view.icons.map((icon) => [icon.key, icon.amount]),
      [['e', 12], ['x', 40], ['g', 500], ['w', 25], ['o', 8], ['s', 4], ['c', 10], ['m', 2]],
    );
    const markup = renderIcons(view);
    assert.match(markup, /data-swl-icon-panel="icons"/);
    assert.ok(markup.includes('data-swl-resource="g"'));
    assert.ok(markup.includes('data-swl-resource-amount="500"'));
    assert.ok(markup.indexOf('data-swl-resource="e"') < markup.indexOf('data-swl-resource="m"'));
  });

  it('never invents an amount for an absent or malformed slot', () => {
    const partial = resourceIconPanel(world({ resources: { g: 7 } }));
    assert.deepEqual(partial.icons, [{ key: 'g', label: 'Gold', amount: 7 }]);
    const markup = renderIcons(partial);
    assert.ok(!markup.includes('data-swl-resource="w"'), 'no wood amount is invented');
    assert.ok(!markup.includes('Wood'), 'no wood label is invented');

    for (const resources of [{}, { g: 'lots' }, { g: Number.NaN }, null]) {
      const empty = resourceIconPanel(world({ resources }));
      assert.deepEqual(empty.icons, []);
      const emptyMarkup = renderIcons(empty);
      assert.match(emptyMarkup, /data-swl-icon-panel="empty"/);
      assert.ok(emptyMarkup.includes(art.NO_ICONS_CAPTION));
      assert.ok(!emptyMarkup.includes('data-swl-resource='));
    }
  });
});

describe('the assault portraits read only the server army and receipt', () => {
  it('draws the army with the server win mark', () => {
    const view = assaultPortraitPanel(bundle(), world(), 0);
    assert.deepEqual(view, {
      portraits: [
        {
          itemId: 7,
          name: 'Marine',
          available: 3,
          allowed: true,
          settled: true,
          won: true,
        },
      ],
      opponent: 'village-9',
    });
    const markup = renderAssault(view);
    assert.match(markup, /data-swl-assault-portraits="roster"/);
    assert.ok(markup.includes('data-swl-unit-id="7"'));
    assert.ok(markup.includes('×3'));
    assert.ok(markup.includes('data-swl-figure-mark="won"'), 'the server win mark is drawn');
  });

  it('draws no win mark for an unsettled answer', () => {
    const view = assaultPortraitPanel(bundle(), world({ privateState: {} }), 0);
    assert.equal(view.portraits[0]!.settled, false);
    assert.equal(view.portraits[0]!.won, null);
    assert.equal(view.opponent, null);
    const markup = renderAssault(view);
    assert.ok(!markup.includes('data-swl-figure-mark="won"'));
    assert.ok(!markup.includes('data-swl-figure-mark="lost"'));
  });

  it('has an explicit empty state when the server publishes no army', () => {
    const view = assaultPortraitPanel(
      bundle(),
      world({ maps: [], privateState: {} }),
      0,
    );
    assert.deepEqual(view, { portraits: [], opponent: null });
    const markup = renderAssault(view);
    assert.match(markup, /data-swl-assault-portraits="empty"/);
    assert.ok(markup.includes(art.NO_ASSAULT_PORTRAITS_CAPTION));
    assert.ok(!markup.includes('data-swl-unit-id='), 'no portrait is invented');
  });
});

describe('the three shells are original, deterministic and inert', () => {
  const source = readFileSync(
    fileURLToPath(new URL('./portraitshells.tsx', import.meta.url)),
    'utf8',
  );

  it('never rolls, grants, charges or sends a command of its own', () => {
    for (const forbidden of [
      /Math\.random/,
      /Date\.now/,
      /push_queue_unit/,
      /pop_queue_unit/,
      /set_strategy/,
      /buy_offer_pack/,
      /\bdispatch\s*\(/,
    ]) {
      assert.ok(!forbidden.test(source), `${forbidden} must not appear in the shells`);
    }
    const view = extendedPortraitPopup(bundle(), world(), 0)!;
    const first = renderToStaticMarkup(React.createElement(art.ExtendedPortraitButton, { view }));
    const second = renderToStaticMarkup(React.createElement(art.ExtendedPortraitButton, { view }));
    assert.equal(first, second, 'the same server state always draws the same SVG');
  });

  it('contains no external asset reference in any drawn SVG', () => {
    const markup = [
      renderButton(extendedPortraitPopup(bundle(), world(), 0)),
      renderIcons(resourceIconPanel(world())),
      renderAssault(assaultPortraitPanel(bundle(), world(), 0)),
    ].join('');
    for (const forbidden of [
      /<image\b/i,
      /\bhref\s*=/i,
      /\bsrc\s*=/i,
      /url\s*\(/i,
      /\.(?:swf|png|jpe?g|gif|webp|svg)\b/i,
      /xlink/i,
      /atlas/i,
      /upstream/i,
      /flash/i,
      /shockwave/i,
      /https?:\/\//i,
    ]) {
      assert.ok(!forbidden.test(markup), `the SVG must not reference ${forbidden}`);
    }
    assert.match(markup, /<svg\b/);
    assert.match(markup, /<rect\b/);
    assert.match(markup, /<circle\b/);
    assert.match(markup, /<path\b/);
  });
});
