import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { buildContent, canonicalise, extractQuestEvents, type QuestMapSnapshot } from './build.ts';
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

describe('hardcore quest rosters', () => {
  // The eight hardcore quests have `elements: []` in the config, so their
  // rosters live in the vendored quest map snapshots. Counts recorded in
  // re/docs/01-network-protocol.md §3.5.
  const EXPECTED_UNITS: Record<string, number> = {
    '100000017': 79, // HC1
    '100000018': 122, // HC2
    '100000019': 114, // HC3
    '100000020': 45, // HC4
    '100000021': 84, // HC5
    '100000022': 153, // HC6
    '100000026': 138, // HC9
    '100000025': 46, // HC10
  };

  it('extracts exactly the eight hardcore rosters', async () => {
    const { bundle } = await buildContent();
    const rosters = bundle.questRosters;
    assert.ok(rosters, 'questRosters is missing from the bundle');
    assert.deepEqual(
      rosters.map((r) => r.questId).sort(),
      Object.keys(EXPECTED_UNITS).sort(),
    );
  });

  it('extracts the exact unit count of every roster', async () => {
    const { bundle } = await buildContent();
    const rosters = bundle.questRosters ?? [];
    assert.equal(rosters.length, 8, 'the bundle has eight quest rosters');
    for (const roster of rosters) {
      assert.equal(
        roster.items.length,
        EXPECTED_UNITS[roster.questId],
        `quest ${roster.questId} roster has the wrong unit count`,
      );
    }
  });

  it('emits unique item:<isoId> refs from unit-typed content items', async () => {
    const { bundle } = await buildContent();
    const byId = new Map(bundle.items.map((i) => [i.id, i]));
    const rosters = bundle.questRosters ?? [];
    assert.equal(rosters.length, 8, 'the bundle has eight quest rosters');
    for (const roster of rosters) {
      const refs = roster.items.map((entry) => entry.ref);
      assert.equal(new Set(refs).size, refs.length, `quest ${roster.questId} has duplicate refs`);
      for (const entry of roster.items) {
        assert.match(entry.ref, /^item:\d+$/);
        const content = byId.get(entry.itemId);
        assert.ok(content, `quest ${roster.questId} references unknown item ${entry.itemId}`);
        assert.equal(content!.type, 'u', `item ${entry.itemId} is not a unit`);
        assert.equal(entry.subcatFunctional, content!.subcat_functional);
      }
    }
  });

  it('keeps the build id stable while carrying the rosters', async () => {
    const first = await buildContent();
    const second = await buildContent();
    assert.equal(second.bundle.buildId, first.bundle.buildId);
    assert.deepEqual(second.bundle.questRosters, first.bundle.questRosters);
    assert.match(first.bundle.buildId, /^[0-9a-f]{64}$/);
  });

  it('does not change the other bundle counts', async () => {
    const { bundle, problems } = await buildContent();
    assert.equal(bundle.items.length, 900);
    assert.equal(bundle.levels.length, 100);
    assert.equal(bundle.goals.length, 91);
    assert.equal(Object.keys(bundle.globals).length, 105);
    assert.equal(bundle.dartsItems.length, 27);
    assert.deepEqual(problems, []);
  });
});

describe('quest event data', () => {
  // Q03 trucks spawn dynamically, so the map has no static truck element: the
  // ref and the arrival count are the client's hard-coded constants recorded in
  // re/data/quests.json (ID_UNIT_TRUCK_1 = 1013, totalTrucksToSave = 3).
  // Q10/Q14's eligible enemies and Q11's civilians ARE on the vendored maps.
  const EVENT_QUEST_IDS = ['100000003', '100000010', '100000011', '100000014'];

  it('has an entry for each of the four event-driven quests', async () => {
    const { bundle, problems } = await buildContent();
    assert.ok(bundle.questEvents, 'questEvents is missing from the bundle');
    assert.deepEqual(Object.keys(bundle.questEvents).sort(), EVENT_QUEST_IDS);
    assert.deepEqual(problems, []);
  });

  it('seeds Q03 truck arrivals from the client constants', async () => {
    const { bundle } = await buildContent();
    assert.deepEqual(bundle.questEvents!['100000003'], {
      questId: '100000003',
      kind: 'truckArrivals',
      refs: ['item:1013'],
      count: 3,
    });
  });

  it('extracts every eligible enemy of Q10 and Q14', async () => {
    const { bundle } = await buildContent();
    for (const [questId, count] of [
      ['100000010', 23],
      ['100000014', 24],
    ] as const) {
      const event = bundle.questEvents![questId]!;
      assert.equal(event.kind, 'eligibleEnemies', `${questId} has the wrong kind`);
      assert.equal(event.count, count, `${questId} has the wrong eligible-enemy count`);
      assert.equal(event.refs.length, count, `${questId} has the wrong number of refs`);
    }
  });

  it('extracts every civilian of Q11', async () => {
    const { bundle } = await buildContent();
    const event = bundle.questEvents!['100000011']!;
    assert.equal(event.kind, 'civilianEvacuations');
    assert.equal(event.count, 12);
    assert.equal(event.refs.length, 12);
  });

  it('emits unique item:<isoId> refs for every extracted event', async () => {
    const { bundle } = await buildContent();
    for (const questId of EVENT_QUEST_IDS) {
      const refs = bundle.questEvents![questId]!.refs;
      assert.equal(new Set(refs).size, refs.length, `quest ${questId} has duplicate refs`);
      for (const ref of refs) assert.match(ref, /^item:\d+$/, `quest ${questId} has a bad ref`);
    }
    // The truck ref addresses an item id, not a static map element.
    assert.deepEqual(bundle.questEvents!['100000003']!.refs, ['item:1013']);
  });

  it('keeps the build id stable with quest events in the bundle', async () => {
    const first = await buildContent();
    const second = await buildContent();
    assert.equal(second.bundle.buildId, first.bundle.buildId);
    assert.deepEqual(second.bundle.questEvents, first.bundle.questEvents);
    assert.match(first.bundle.buildId, /^[0-9a-f]{64}$/);
  });

  it('leaves the rosters and the other bundle counts unchanged', async () => {
    const { bundle } = await buildContent();
    assert.equal(bundle.items.length, 900);
    assert.equal(bundle.levels.length, 100);
    assert.equal(bundle.goals.length, 91);
    assert.equal(Object.keys(bundle.globals).length, 105);
    assert.equal(bundle.dartsItems.length, 27);
    assert.equal(bundle.questRosters?.length, 8);
  });
});

describe('quest event extraction validation', () => {
  it('rejects a source whose quest id has no vendored snapshot', () => {
    const problems: string[] = [];
    const events = extractQuestEvents(new Map(), new Map(), problems, [
      { questId: '999999999', kind: 'eligibleEnemies', groupTypes: ['LONG_RANGE'] },
    ]);
    assert.deepEqual(events, {});
    assert.ok(problems.some((p) => p.includes('999999999')));
  });

  it('rejects an empty selection and a mismatched snapshot pid', () => {
    const problems: string[] = [];
    const snapshots = new Map<string, QuestMapSnapshot>([
      ['100000010', { playerInfo: { pid: '999' }, maps: [{ items: {} }] }],
    ]);
    const events = extractQuestEvents(new Map(), snapshots, problems, [
      { questId: '100000010', kind: 'eligibleEnemies', groupTypes: ['LONG_RANGE'] },
    ]);
    assert.deepEqual(events, {});
    assert.ok(problems.some((p) => p.includes('playerInfo.pid')));
    assert.ok(problems.some((p) => p.includes('has no eligibleEnemies elements')));
  });
});
