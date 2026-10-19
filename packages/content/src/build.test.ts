import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { buildContent, canonicalise } from './build.ts';
import { applyPatch, parsePointer } from './patch.ts';

describe('JSON Pointer', () => {
  it('unescapes the reference tokens', () => {
    assert.deepEqual(parsePointer('/a~1b/c~0d'), ['a/b', 'c~d']);
  });

  it('rejects a pointer that does not start with a slash', () => {
    assert.throws(() => parsePointer('a/b'), /invalid JSON pointer/);
  });
});

describe('JSON Patch', () => {
  it('appends to an array', () => {
    const doc = { items: [1, 2] };
    const out = applyPatch(doc, [{ op: 'add', path: '/items/-', value: 3 }]);
    assert.deepEqual(out, { items: [1, 2, 3] });
  });

  it('adds an object member', () => {
    const doc = { items: [{ id: 1 }] };
    const out = applyPatch(doc, [{ op: 'add', path: '/items/0/name', value: 'x' }]);
    assert.deepEqual(out, { items: [{ id: 1, name: 'x' }] });
  });

  it('replaces a whole member', () => {
    const doc = { a: 1, b: 2 };
    const out = applyPatch(doc, [{ op: 'replace', path: '/b', value: 9 }]);
    assert.deepEqual(out, { a: 1, b: 9 });
  });

  it('refuses to replace a member that does not exist', () => {
    assert.throws(
      () => applyPatch({ a: 1 }, [{ op: 'replace', path: '/missing', value: 1 }]),
      /missing member/,
    );
  });

  it('refuses an operation it does not implement rather than ignoring it', () => {
    assert.throws(
      () =>
        applyPatch({ a: 1 }, [
          { op: 'frobnicate' as unknown as 'add', path: '/a', value: 1 },
        ]),
      /unsupported patch operation/,
    );
  });

  it('does not mutate its input', () => {
    const doc = { items: [1] };
    applyPatch(doc, [{ op: 'add', path: '/items/-', value: 2 }]);
    assert.deepEqual(doc, { items: [1] });
  });
});

describe('the content build', () => {
  it('reproduces the upstream server post-patch counts', async () => {
    const { bundle, problems } = await buildContent();

    // The upstream server logs exactly these numbers after applying the patches.
    assert.equal(bundle.items.length, 900);
    assert.equal(bundle.levels.length, 100);
    assert.equal(bundle.goals.length, 91);
    assert.equal(Object.keys(bundle.globals).length, 105);
    assert.equal(bundle.dartsItems.length, 27);

    // 41 distinct property keys, 24 subcat_functional values.
    assert.equal(Object.keys(bundle.propertyKeys).length, 41);
    assert.equal(Object.keys(bundle.subcatFunctionals).length, 24);

    // The build must be clean.
    assert.deepEqual(problems, []);
  });

  it('applies the five patches in the order patches.txt lists them', async () => {
    const { bundle } = await buildContent();
    assert.deepEqual(bundle.patchesApplied, [
      'atom_fusion_item',
      'unit_patch',
      'atom_fusion_items_data',
      'atom_fusion_powerup',
      'targets',
    ]);
  });

  it('produces a stable build id', async () => {
    const first = await buildContent();
    const second = await buildContent();
    assert.equal(second.bundle.buildId, first.bundle.buildId);
    assert.match(first.bundle.buildId, /^[0-9a-f]{64}$/);
  });

  it('canonicalises deterministically regardless of key order', () => {
    assert.equal(canonicalise({ b: 1, a: 2 }), canonicalise({ a: 2, b: 1 }));
  });

  it('covers the whole 1307-1431 wave with stats', async () => {
    const { bundle } = await buildContent();
    const wave = bundle.items.filter((i) => i.id >= 1307 && i.id <= 1431);
    assert.ok(wave.length > 110, `only ${wave.length} wave items`);
    for (const item of wave) {
      assert.ok(item.attack > 0, `item ${item.id} has no attack`);
      assert.ok(item.life > 0, `item ${item.id} has no life`);
      assert.ok(item.attack_interval > 0, `item ${item.id} has no attack interval`);
    }
  });

  it('leaves only a handful of client-known ids without config data', async () => {
    const { bundle } = await buildContent();
    assert.ok(
      bundle.clientOnlyItemIds.length <= 10,
      `${bundle.clientOnlyItemIds.length} client-only ids`,
    );
  });
});
