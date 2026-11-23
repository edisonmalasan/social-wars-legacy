/**
 * The at-rest visibility contract of the interface root.
 *
 * The original game shows the HUD, the neighbour strip and the bottom
 * navigation at rest. Everything else — storage, the store, the mission
 * list, the build list — is a surface the player opens on request, one at a
 * time. This test renders the real tree with `react-dom/server`: a class that
 * is absent from the markup is a panel that cannot cover the world.
 *
 * The dialog is deliberately outside the surface state. Its priority stack
 * stays exactly as it was; opening a surface must not change which dialog the
 * one shared slot hosts.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve as resolvePath } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { registerHooks } from 'node:module';
import ts from 'typescript';

import * as React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

import type { Neighbour, WorldSnapshot } from '@swl/client';
import type { ContentBundle } from '@swl/content';
import { CLOSED_DIALOG, openDialog } from '@swl/client';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolvePath(HERE, '../../../..');
const BROWSER_ENTRY = resolvePath(ROOT, 'packages/art/browser.ts');

// The interface is JSX, which Node's native type stripper does not transform.
// A tiny loader transpiles only the .tsx files in this test's graph; the model
// modules stay on the native stripper. The art browser entry is mapped because
// it is a package the client does not depend on directly.
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier === '@swl/art/browser') {
      return { url: pathToFileURL(BROWSER_ENTRY).href, shortCircuit: true };
    }
    return nextResolve(specifier, context);
  },
  load(url, context, nextLoad) {
    if (url.endsWith('.tsx')) {
      const source = readFileSync(fileURLToPath(url), 'utf8');
      const { outputText } = ts.transpileModule(source, {
        compilerOptions: {
          jsx: ts.JsxEmit.ReactJSX,
          module: ts.ModuleKind.ESNext,
          target: ts.ScriptTarget.ESNext,
        },
        fileName: url,
      });
      return { format: 'module', shortCircuit: true, source: outputText };
    }
    return nextLoad(url, context);
  },
});

import type { ActiveSurface, RootProps } from './root.tsx';

const { Root, setSurfaceHost, toggleSurface } = await import('./root.tsx') as {
  Root: (props: RootProps) => React.JSX.Element;
  setSurfaceHost: (patch: { surface: ActiveSurface; setSurface: (next: ActiveSurface) => void }) => void;
  toggleSurface: (current: ActiveSurface, requested: Exclude<ActiveSurface, 'none'>) => ActiveSurface;
};

function bundle(): ContentBundle {
  return {
    items: [
      { id: 1, name: 'Command Center', type: 'b', trains_ids: [2], training_time: 0 },
      { id: 2, name: 'Worker', type: 'u' },
    ],
    levels: [],
    goals: [],
    globals: {},
    collections: [],
    inventoryItems: {},
    offerPacks: [],
    magics: [],
    expansionPrices: [{ coins: 100, cash: 1 }],
    categories: {},
    questRosters: [],
    questEvents: {},
  } as unknown as ContentBundle;
}

function world(): WorldSnapshot {
  return {
    maps: [{ id: 0, items: { 1: [1, 4, 4, 0, 0] }, store: {} }],
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
    privateState: {},
  } as unknown as WorldSnapshot;
}

function neighbour(): Neighbour {
  return {
    id: 'village',
    name: 'Village',
    level: 1,
    xp: 0,
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
    static: true,
  };
}

function render(surface: ActiveSurface, extra: Partial<RootProps> = {}): string {
  setSurfaceHost({ surface, setSurface: () => {} });
  const props: RootProps = {
    world: world(),
    bundle: bundle(),
    neighbours: [neighbour()],
    selected: 1,
    selectedIso: 1,
    ...extra,
  };
  return renderToStaticMarkup(React.createElement(Root, props));
}

/** The root element each gated panel draws, keyed by the surface that owns it. */
const PANEL_CLASS: Record<Exclude<ActiveSurface, 'none'>, string> = {
  build: 'swl-build-menu',
  goals: 'swl-goals',
  expansion: 'swl-expansion',
  inventory: 'swl-inventory',
  chapters: 'swl-chapters',
  info: 'swl-info',
  recruit: 'swl-recruit',
  store: 'swl-store',
  controls: 'swl-chrome',
  launchers: 'swl-original-art-launcher',
  magiclab: 'swl-magiclab',
  spellbook: 'swl-spellbook',
};

function hasClass(markup: string, name: string): boolean {
  return markup.includes(`class="${name}"`) || markup.includes(`class="${name} `);
}

describe('the active surface', () => {
  it('opens one surface and closes it again when the same control is pressed', () => {
    assert.equal(toggleSurface('none', 'build'), 'build');
    assert.equal(toggleSurface('build', 'build'), 'none');
    // A different request replaces the current surface; two are never open.
    assert.equal(toggleSurface('build', 'inventory'), 'inventory');
    assert.equal(toggleSurface('inventory', 'goals'), 'goals');
  });

  it('shows only the HUD, neighbours and the build control at rest', () => {
    const markup = render('none');
    assert.ok(hasClass(markup, 'swl-hud'), 'the HUD is always visible');
    assert.ok(hasClass(markup, 'swl-neighbours'), 'the neighbours are at rest');
    assert.ok(markup.includes('data-swl-surface="build"'), 'the build control is at rest');
    for (const name of Object.values(PANEL_CLASS)) {
      assert.ok(!hasClass(markup, name), `${name} must not be mounted at rest`);
    }
  });

  it('opens the build list on request and hides the neighbours while it is open', () => {
    const markup = render('build');
    assert.ok(hasClass(markup, 'swl-build-menu'), 'the build list opens');
    assert.ok(!hasClass(markup, 'swl-neighbours'), 'the neighbours step aside');
    assert.ok(hasClass(markup, 'swl-hud'), 'the HUD stays');
    assert.ok(markup.includes('data-swl-surface="build"'), 'the control can close it again');
  });

  it('never has more than one surface mounted', () => {
    for (const [surface, own] of Object.entries(PANEL_CLASS) as [
      Exclude<ActiveSurface, 'none'>,
      string,
    ][]) {
      const markup = render(surface);
      assert.ok(hasClass(markup, own), `${surface} mounts its own panel`);
      for (const [other, name] of Object.entries(PANEL_CLASS)) {
        if (other === surface) continue;
        assert.ok(!hasClass(markup, name), `${surface} must not also mount ${other}`);
      }
      assert.ok(!hasClass(markup, 'swl-neighbours'), `${surface} hides the neighbours`);
      assert.ok(hasClass(markup, 'swl-hud'), `${surface} keeps the HUD`);
    }
  });

  it('keeps the shared dialog stack independent of the active surface', () => {
    const dialog = openDialog(CLOSED_DIALOG, 'quest-briefing', 'confirm', 'A quest');
    const closed = render('none', { dialog: CLOSED_DIALOG });
    assert.ok(!hasClass(closed, 'swl-dialog-backdrop'), 'no dialog is drawn when closed');

    const openAtRest = render('none', { dialog });
    assert.ok(hasClass(openAtRest, 'swl-dialog-backdrop'), 'the dialog still opens at rest');
    assert.ok(openAtRest.includes('A quest'), 'the dialog keeps its title');

    const openWithSurface = render('inventory', { dialog });
    assert.ok(hasClass(openWithSurface, 'swl-dialog-backdrop'), 'a surface does not eat the dialog');
    assert.ok(openWithSurface.includes('A quest'), 'the dialog keeps its title with a surface open');
  });
});
