import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import type { WorldSnapshot } from '@swl/client';

import {
  SOUL_MIXER_HELP,
  SOUL_MIXER_TURBINA_LABEL,
  SOUL_MIXER_TURBINA_PLACEHOLDER,
  formatTurbinaRemaining,
  soulMixerDialog,
  soulMixerTurbina,
} from './state.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

/** A world with no published turbine state, as a fresh server answer has. */
function world(privateState: Record<string, unknown> = {}): WorldSnapshot {
  return {
    maps: [{ id: 0, items: {} }],
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
    privateState,
  } as unknown as WorldSnapshot;
}

describe('the soul-mixer help literal', () => {
  it('is the recovered four-step copy, verbatim down to the stray final line', async () => {
    const inventory = JSON.parse(
      await readFile(path.join(repoRoot(), 're/data/ui-screens.json'), 'utf8'),
    ) as { screens: { path: string; literals: string[] }[] };
    const help = inventory.screens.find(
      (screen) => screen.path === 'popups/PopupSoulMixerHelp.as',
    );
    assert.ok(help, 'the help screen is not in the inventory');
    // The inventory keeps the AS3 source escapes, so `\n` is two characters
    // there; the drawn copy turns each one into a real line break.
    assert.equal(
      SOUL_MIXER_HELP,
      help!.literals[0]!.replace(/\\n/g, '\n'),
    );
    assert.match(SOUL_MIXER_HELP, /POWERUP button/);
    assert.match(SOUL_MIXER_HELP, /SPEEDUP button/);
    assert.ok(SOUL_MIXER_HELP.endsWith('combinations\n.'));
  });
});

describe('the soul-mixer turbine presentation', () => {
  it('reports no timer when the server published no state', () => {
    assert.deepEqual(soulMixerTurbina(world()), {
      available: false,
      state: null,
      remainingSeconds: null,
    });
    assert.match(SOUL_MIXER_TURBINA_PLACEHOLDER, /No active fusion timer/);
  });

  it('copies only the state the server actually wrote', () => {
    const view = soulMixerTurbina(world({ soulMixer: { state: 'training', remainingSeconds: 95 } }));
    assert.deepEqual(view, {
      available: true,
      state: 'training',
      remainingSeconds: 95,
    });
    assert.equal(formatTurbinaRemaining(view.remainingSeconds!), '01:35');
  });

  it('never derives a countdown from a timestamp or a training time', () => {
    // The upstream saved a fusion `ts` in `atom_fusion[6]`, but the new server
    // has no applier case and the output rule was never recovered, so a raw
    // timestamp must never be turned into a remaining time here.
    const view = soulMixerTurbina(world({ atom_fusion: [, , , , , , { ts: 1_700_000_000 }] }));
    assert.equal(view.available, false);
    assert.equal(view.remainingSeconds, null);
  });

  it('treats malformed and empty records as absent, never as a state', () => {
    for (const raw of [42, 'training', [], {}, { state: '' }, { remainingSeconds: 'soon' }]) {
      assert.equal(soulMixerTurbina(world({ soulMixer: raw })).available, false);
    }
    // A finite negative server value is clamped to zero, not invented.
    assert.equal(
      soulMixerTurbina(world({ soulMixer: { remainingSeconds: -5, state: 'done' } }))
        .remainingSeconds,
      0,
    );
  });

  it('uses the one shared dialog with a single stable id', () => {
    assert.deepEqual(soulMixerDialog(), {
      id: 'soulmixer-help',
      kind: 'alert',
      title: 'Soul Mixer Help',
    });
    assert.equal(SOUL_MIXER_TURBINA_LABEL, 'Remaining time:');
  });
});
