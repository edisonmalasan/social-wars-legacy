/**
 * Tests for the original unit / training-queue portraits.
 *
 * The portrait module is JSX-free so Node's native TypeScript stripper can
 * load it; a small `registerHooks` loader lets these tests render the real
 * component with `react-dom/server`. Every assertion below checks that the
 * portrait draws only the state the server published.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { registerHooks, stripTypeScriptTypes } from 'node:module';
import { fileURLToPath } from 'node:url';

import * as React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

import type { TrainingView } from '@swl/client';

import type { UnitPortraitView } from './unitportraits.tsx';

registerHooks({
  load(url, context, nextLoad) {
    if (url.endsWith('unitportraits.tsx')) {
      const source = readFileSync(fileURLToPath(url), 'utf8');
      return { format: 'module', shortCircuit: true, source: stripTypeScriptTypes(source) };
    }
    return nextLoad(url, context);
  },
});

const art = await import('./unitportraits.tsx');

/** A server queue view we can bend into a malformed shape. */
function queue(patch: Partial<TrainingView> = {}): TrainingView {
  return { queued: 0, unitItemId: 0, remainingSeconds: 0, readyToTake: false, ...patch };
}

const units = [{ itemId: 1007, name: 'Marine' }];

function renderQueue(value: TrainingView | null | undefined, names = units): string {
  return renderToStaticMarkup(
    React.createElement(art.TrainingQueuePortraits, { queue: value, units: names }),
  );
}

describe('the training-queue portrait read', () => {
  it('is empty when the queue is absent or its fields are malformed', () => {
    assert.equal(art.queuePortrait(null), null);
    assert.equal(art.queuePortrait(undefined), null);
    assert.equal(art.queuePortrait(queue()), null);
    assert.equal(art.queuePortrait(queue({ queued: -2, unitItemId: 1007 })), null);
    assert.equal(art.queuePortrait(queue({ queued: Number.NaN, unitItemId: 1007 })), null);
    assert.equal(art.queuePortrait(queue({ queued: 2, unitItemId: 0 })), null);
    assert.equal(art.queuePortrait(queue({ queued: 2, unitItemId: Number.NaN })), null);

    for (const value of [null, undefined, queue(), queue({ queued: 2, unitItemId: 0 })]) {
      const markup = renderQueue(value);
      assert.match(markup, /data-swl-portraits="queue-empty"/);
      assert.ok(!markup.includes('data-swl-portrait="'), 'no portrait is drawn');
      assert.ok(!markup.includes('data-swl-unit-id='), 'no unit id is invented');
      assert.ok(!markup.includes(art.TRAINING_CAPTION), 'no charge state is invented');
      assert.ok(!markup.includes(art.READY_CAPTION), 'no ready state is invented');
    }
    assert.ok(renderQueue(queue()).includes(art.EMPTY_CAPTION));
  });

  it('renders the queued unit id, count and content name exactly', () => {
    const view = art.queuePortrait(queue({ queued: 3, unitItemId: 1007 }), units);
    assert.deepEqual(view, {
      itemId: 1007,
      name: 'Marine',
      count: 3,
      animation: 'training',
    });
    const markup = renderQueue(queue({ queued: 3, unitItemId: 1007, remainingSeconds: 42 }));
    assert.ok(markup.includes('data-swl-portrait="'), 'a portrait is drawn');
    assert.ok(markup.includes('data-swl-unit-id="1007"'), 'the server id is shown');
    assert.ok(markup.includes('data-swl-portrait-count="3"'), 'the server count is shown');
    assert.ok(markup.includes('×3'), 'the count is printed verbatim');
    assert.ok(markup.includes('Marine'), 'the content name is shown');
    assert.ok(!markup.includes('42'), 'a countdown is not a unit count');
  });

  it('does not invent a name when content does not name the server id', () => {
    const view = art.queuePortrait(queue({ queued: 1, unitItemId: 4242 }), units);
    assert.deepEqual(view, {
      itemId: 4242,
      name: null,
      count: 1,
      animation: 'training',
    });
    assert.equal(art.portraitLabel(view!), 'Unit 4242');
    const markup = renderQueue(queue({ queued: 1, unitItemId: 4242 }));
    assert.ok(markup.includes('data-swl-unit-id="4242"'));
    assert.ok(!markup.includes('Marine'), 'another unit is never substituted');
  });

  it('shows ready / not charged only when the server queue says so', () => {
    const training = art.queuePortrait(queue({ queued: 2, unitItemId: 1007, readyToTake: false }), units);
    assert.equal(training!.animation, 'training');
    assert.equal(art.portraitCaption(training!), art.TRAINING_CAPTION);
    const trainingMarkup = renderQueue(queue({ queued: 2, unitItemId: 1007, readyToTake: false }));
    assert.ok(trainingMarkup.includes('data-swl-animation="training"'));
    assert.ok(trainingMarkup.includes('data-swl-animation-mark="charging"'));
    assert.ok(trainingMarkup.includes(art.TRAINING_CAPTION));
    assert.ok(!trainingMarkup.includes(art.READY_CAPTION));

    const ready = art.queuePortrait(queue({ queued: 2, unitItemId: 1007, readyToTake: true }), units);
    assert.equal(ready!.animation, 'ready');
    assert.equal(art.portraitCaption(ready!), art.READY_CAPTION);
    const readyMarkup = renderQueue(queue({ queued: 2, unitItemId: 1007, readyToTake: true }));
    assert.ok(readyMarkup.includes('data-swl-animation="ready"'));
    assert.ok(readyMarkup.includes('data-swl-animation-mark="ready"'));
    assert.ok(readyMarkup.includes(art.READY_CAPTION));
    assert.ok(!readyMarkup.includes(art.TRAINING_CAPTION));

    // A malformed flag is never promoted to a ready unit.
    const malformed = queue({ queued: 2, unitItemId: 1007, readyToTake: 'true' as unknown as boolean });
    assert.equal(art.queuePortrait(malformed)!.animation, 'training');
    assert.ok(!renderQueue(malformed).includes(art.READY_CAPTION));
  });
});

describe('the owned-unit portraits', () => {
  it('draws only the units and counts the server owns', () => {
    const owned = art.ownedPortraits([
      { itemId: 7, name: 'Marine', count: 5 },
      { itemId: 8, name: 'Archer', count: 0 },
    ]);
    assert.deepEqual(
      owned.map((view) => [view.itemId, view.name, view.count, view.animation]),
      [
        [7, 'Marine', 5, 'owned'],
        [8, 'Archer', 0, 'owned'],
      ],
    );
    const markup = renderToStaticMarkup(
      React.createElement(art.OwnedUnitPortraits, {
        units: [
          { itemId: 7, name: 'Marine', count: 5 },
          { itemId: 8, name: 'Archer', count: 0 },
        ],
      }),
    );
    assert.ok(markup.includes('data-swl-unit-id="7"'));
    assert.ok(markup.includes('×5'));
    assert.ok(markup.includes('data-swl-unit-id="8"'));
    assert.ok(markup.includes('×0'));
    assert.ok(!markup.includes(art.READY_CAPTION), 'an owned unit is not a ready queue unit');
  });

  it('skips malformed rows without inventing a unit or a count', () => {
    const rows = Object.freeze([
      { itemId: Number.NaN, name: 'Ghost', count: 2 },
      { itemId: 0, name: 'None', count: 1 },
      { itemId: -3, name: 'Bad', count: 1 },
      { itemId: 7, name: 'Marine', count: -1 },
    ]);
    assert.deepEqual(art.ownedPortraits(rows), []);
    assert.equal(art.ownedPortrait(null), null);
    assert.equal(art.ownedPortrait({ itemId: 7, name: 'Marine', count: 2 })!.count, 2);
  });
});

describe('the portrait is original, deterministic and inert', () => {
  const source = readFileSync(
    fileURLToPath(new URL('./unitportraits.tsx', import.meta.url)),
    'utf8',
  );

  it('never rolls, grants, charges or sends a command of its own', () => {
    for (const forbidden of [
      /Math\.random/,
      /Date\.now/,
      /push_queue_unit/,
      /pop_queue_unit/,
      /\bcommand\s*\(/,
      /\bdispatch\s*\(/,
      /onClick/,
      /onTrain/,
      /onTake/,
    ]) {
      assert.ok(!forbidden.test(source), `${forbidden} must not appear in the portrait`);
    }
    const view = art.ownedPortrait({ itemId: 7, name: 'Marine', count: 3 })!;
    const first = renderToStaticMarkup(React.createElement(art.UnitPortrait, { view }));
    const second = renderToStaticMarkup(React.createElement(art.UnitPortrait, { view }));
    assert.equal(first, second, 'the same server state always draws the same SVG');
  });

  it('contains no external asset reference in the drawn SVG', () => {
    const markup = [
      art.queuePortrait(queue({ queued: 1, unitItemId: 1007, readyToTake: true }), units),
      art.queuePortrait(queue({ queued: 1, unitItemId: 1008, readyToTake: false }), units),
      art.ownedPortrait({ itemId: 7, name: 'Marine', count: 2 }),
    ]
      .filter((view): view is UnitPortraitView => view !== null)
      .map((view) => renderToStaticMarkup(React.createElement(art.UnitPortrait, { view })))
      .join('');
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
