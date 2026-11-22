/**
 * Tests for the resource-button / icon-chrome family.
 *
 * The module is JSX-free so Node's native TypeScript stripper can load it;
 * a small `registerHooks` loader renders the real components with
 * `react-dom/server`. Every assertion checks that the chrome draws only server
 * values, sends only catalogue commands and uses only original inline art.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { registerHooks, stripTypeScriptTypes } from 'node:module';
import { fileURLToPath } from 'node:url';

import * as React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

import type { WorldSnapshot } from '@swl/client';
import type { ContentBundle } from '@swl/content';

import {
  RESOURCE_BUTTONS_NO_AMOUNTS,
  RESOURCE_BUTTONS_NO_STATE,
  RESOURCE_BUTTONS_NOTE,
  resourceButtonsDialog,
  resourceButtonsPanel,
} from './state.ts';

registerHooks({
  load(url, context, nextLoad) {
    if (url.endsWith('resourcebuttons.tsx')) {
      const source = readFileSync(fileURLToPath(url), 'utf8');
      return { format: 'module', shortCircuit: true, source: stripTypeScriptTypes(source) };
    }
    return nextLoad(url, context);
  },
});

const art = await import('./resourcebuttons.tsx');

function bundle(globals: Record<string, unknown> = {}): ContentBundle {
  return {
    globals: {
      BASE_RESOURCE_LIMITS: { e: 30, g: 20000, w: 20000, o: 20000, s: 20000, m: 100 },
      MARKET_AMOUNT_TRADE: [100, 200],
      ...globals,
    },
    items: [],
    levels: [],
    categories: {},
    magics: [],
    offerPacks: [],
    collections: [],
    expansionPrices: [],
  } as unknown as ContentBundle;
}

function world(resources: Record<string, unknown> | null): WorldSnapshot {
  return {
    maps: [{ id: 0, items: {} }],
    resources: resources as Record<string, number>,
    privateState: {},
  } as unknown as WorldSnapshot;
}

const SERVER = { e: 12, x: 34, g: 56, w: 78, o: 90, s: 11, c: 22, m: 33 };

function render(view: ReturnType<typeof resourceButtonsPanel>): string {
  return renderToStaticMarkup(
    React.createElement(art.ResourceButtonsPanel, { view, onCommand: () => {} }),
  );
}

describe('the resource-button chrome read', () => {
  it('is empty when the server published no resource state', () => {
    for (const raw of [null, {}, undefined]) {
      const view = resourceButtonsPanel(bundle(), world(raw as null));
      assert.deepEqual(view.shortcuts, []);
      assert.ok(view.emptyMessages.includes(RESOURCE_BUTTONS_NO_STATE));
      const markup = render(view);
      assert.match(markup, /data-swl-empty="true"/);
      assert.ok(markup.includes(RESOURCE_BUTTONS_NO_STATE));
      assert.ok(!markup.includes('data-swl-server="value"'), 'no value is invented');
      assert.ok(!markup.includes('data-swl-command='), 'no command button is drawn');
      assert.ok(!markup.includes('data-swl-resource='), 'no shortcut row is drawn');
    }
  });

  it('is empty for a malformed wallet rather than drawing zeroes', () => {
    const view = resourceButtonsPanel(
      bundle(),
      world({ g: 'lots', w: Number.NaN, o: null, s: [], e: -1 }),
    );
    assert.deepEqual(view.shortcuts, []);
    assert.ok(view.emptyMessages.includes(RESOURCE_BUTTONS_NO_STATE));
    const markup = render(view);
    assert.match(markup, /data-swl-empty="true"/);
    assert.ok(!markup.includes('>0<'), 'a missing key never becomes a zero');
  });

  it('displays only the server values the wallet actually published', () => {
    const view = resourceButtonsPanel(bundle(), world(SERVER));
    assert.deepEqual(
      view.shortcuts.map((row) => [row.key, row.value]),
      [
        ['e', 12], ['x', 34], ['g', 56], ['w', 78],
        ['o', 90], ['s', 11], ['c', 22], ['m', 33],
      ],
    );
    const markup = render(view);
    for (const [key, value] of Object.entries(SERVER)) {
      assert.match(
        markup,
        new RegExp(`data-swl-resource="${key}"[\\s\\S]*?data-swl-server="value">${value}<`),
        `the server's ${key} is shown verbatim`,
      );
    }
    assert.equal((markup.match(/data-swl-server="value"/g) ?? []).length, 8);
    assert.equal(view.note, RESOURCE_BUTTONS_NOTE);
  });

  it('skips a malformed key without hiding the valid ones', () => {
    const view = resourceButtonsPanel(
      bundle(),
      world({ ...SERVER, o: 'ninety', s: Number.NaN }),
    );
    assert.deepEqual(view.shortcuts.map((row) => row.key), ['e', 'x', 'g', 'w', 'c', 'm']);
    const markup = render(view);
    assert.ok(!markup.includes('data-swl-resource="o"'));
    assert.ok(!markup.includes('data-swl-resource="s"'));
    assert.ok(markup.includes('data-swl-resource="w"'));
  });

  it('shows the content limit as text only, never as a calculated cap', () => {
    const view = resourceButtonsPanel(bundle(), world(SERVER));
    const gold = view.shortcuts.find((row) => row.key === 'g')!;
    assert.equal(gold.limit, 20000);
    const mana = view.shortcuts.find((row) => row.key === 'm')!;
    assert.equal(mana.limit, 100);
    assert.equal(view.shortcuts.find((row) => row.key === 'c')!.limit, null);
    const markup = render(view);
    assert.match(markup, /content limit 20000/);
  });
});

describe('the resource-button trade gesture', () => {
  it('emits exactly the catalogue trade_resource commands from content amounts', () => {
    const view = resourceButtonsPanel(bundle(), world(SERVER));
    const wood = view.shortcuts.find((row) => row.key === 'w')!;
    assert.deepEqual(wood.trade.map((command) => command.args), [
      ['w', 0, 100],
      ['w', 0, 200],
    ]);
    for (const command of wood.trade) {
      assert.equal(command.name, 'trade_resource');
      assert.equal(command.map, 0);
    }
    for (const key of ['e', 'x', 'g', 'c', 'm']) {
      assert.deepEqual(view.shortcuts.find((row) => row.key === key)!.trade, []);
    }
  });

  it('draws the exact command name and args on every trade button', () => {
    const markup = render(resourceButtonsPanel(bundle(), world(SERVER)));
    assert.deepEqual(
      [...markup.matchAll(/data-swl-command="([^"]+)" data-swl-command-args="([^"]+)"/g)].map(
        (match) => [match[1], match[2]],
      ),
      [
        ['trade_resource', 'w,0,100'],
        ['trade_resource', 'w,0,200'],
        ['trade_resource', 'o,0,100'],
        ['trade_resource', 'o,0,200'],
        ['trade_resource', 's,0,100'],
        ['trade_resource', 's,0,200'],
      ],
    );
  });

  it('offers no trade buttons when the content lists no amounts', () => {
    const view = resourceButtonsPanel(
      bundle({ MARKET_AMOUNT_TRADE: 'none' }),
      world(SERVER),
    );
    assert.ok(view.emptyMessages.includes(RESOURCE_BUTTONS_NO_AMOUNTS));
    assert.ok(view.shortcuts.every((row) => row.trade.length === 0));
    const markup = render(view);
    assert.ok(!markup.includes('data-swl-command='));
  });

  it('computes no grant, price or countdown of its own', () => {
    const view = resourceButtonsPanel(bundle(), world(SERVER));
    // The view is a fixed reading: no computed state can be added unnoticed.
    assert.deepEqual(Object.keys(view).sort(), [
      'emptyMessages', 'note', 'shortcuts', 'tab', 'title',
    ]);
    assert.deepEqual(Object.keys(view.shortcuts[0]!).sort(), [
      'key', 'label', 'limit', 'trade', 'value',
    ]);
    for (const row of view.shortcuts) {
      assert.equal(row.value, SERVER[row.key as keyof typeof SERVER]);
      for (const command of row.trade) {
        assert.deepEqual(Object.keys(command).sort(), ['args', 'map', 'name']);
        assert.equal(command.args.length, 3);
        assert.ok([100, 200].includes(Number(command.args[2])));
      }
    }
    const markup = render(view);
    for (const forbidden of [
      'data-swl-grant', 'data-swl-price', 'data-swl-countdown', 'data-swl-remaining',
    ]) {
      assert.ok(!markup.includes(forbidden), `no invented readout: ${forbidden}`);
    }
    assert.ok(!/Next in|countdown|\d+s\b/i.test(markup), 'no client-side timer');
    assert.deepEqual(resourceButtonsDialog(), {
      id: 'resourcebuttons-panel',
      kind: 'alert',
      title: 'Resources',
    });
  });
});

describe('the original inline art', () => {
  it('has no external reference in its source or its rendered markup', () => {
    const source = readFileSync(
      fileURLToPath(new URL('./resourcebuttons.tsx', import.meta.url)),
      'utf8',
    );
    const markup = render(resourceButtonsPanel(bundle(), world(SERVER)));
    const empty = render(resourceButtonsPanel(bundle(), world(null)));
    const launcher = renderToStaticMarkup(React.createElement(art.ResourceButtonsLauncher));
    const all = `${source}\n${markup}\n${empty}\n${launcher}`;
    for (const forbidden of [
      'xlink', 'href=', '<image', '<use', 'foreignObject', 'url(', '@import', '.png', '.swf', '.jpg',
    ]) {
      assert.ok(!all.includes(forbidden), `no external art reference: ${forbidden}`);
    }
    for (const authored of [
      'data-swl-art="resource-badge"',
      'data-swl-art="resource-icon"',
      'data-swl-art="resource-tab"',
      'data-swl-art="resource-empty"',
    ]) {
      assert.ok(all.includes(authored), `${authored} is drawn inline`);
    }
  });

  it('publishes a UI-only launcher state with no command of its own', () => {
    art.setResourceButtonsHost({ open: false });
    assert.deepEqual(art.resourceButtonsHost(), { open: false });
    art.setResourceButtonsHost({ open: true });
    const markup = renderToStaticMarkup(React.createElement(art.ResourceButtonsLauncher));
    assert.match(markup, /data-swl-open="true"/);
    assert.ok(!markup.includes('data-swl-command='), 'the launcher sends no command');
    art.closeResourceButtonsPanel();
    assert.deepEqual(art.resourceButtonsHost(), { open: false });
  });
});
