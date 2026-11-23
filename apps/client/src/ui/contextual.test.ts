/**
 * The contextual panels' palette contract.
 *
 * Phase 1 gave the game bar, the bottom nav and the tutorial the original's
 * olive and gold. This file keeps the panels that open on demand on that same
 * palette, and proves that doing so did not add an at-rest surface: the build
 * list, the info panel, the store's item buttons and the quest bodies are
 * drawings of the same game, not a second, dark-slate interface.
 *
 * Everything here reads source text, the way the chrome and tutorial tests
 * do. No mounted DOM, no screenshot baseline and no gameplay state is needed.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';

function source(name: string): string {
  return readFileSync(path.join(process.cwd(), 'apps/client/src/ui', name), 'utf8');
}

const css = source('css.ts');
const root = source('root.tsx');
const info = source('info.tsx');
const neighbours = source('neighbours.tsx');
const storeitems = source('storeitems.tsx');
const quests = source('quests.tsx');

/** A declaration from the shared token block. */
function token(name: string): string {
  const block = /:root\s*\{([^}]*)\}/.exec(css);
  assert.ok(block, 'the shared token block is missing');
  const match = new RegExp(`${name}:\\s*([^;]+);`).exec(block![1]!);
  assert.ok(match, `${name} token is missing`);
  return match![1]!.trim();
}

/** The bodies of every stylesheet rule with this exact selector, joined. */
function rule(selector: string): string {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const bodies = [...css.matchAll(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`, 'g'))].map(
    (match) => match[1]!,
  );
  assert.ok(bodies.length > 0, `${selector} has no stylesheet rule`);
  return bodies.join('\n');
}

describe('the olive-and-gold contextual panels', () => {
  it('keeps one shared set of game tokens', () => {
    assert.equal(token('--swl-olive'), '#616807');
    assert.equal(token('--swl-ochre'), '#e9dd51');
    assert.match(token('--swl-game-bar'), /var\(--swl-olive\)/);
    assert.equal(token('--swl-bubble'), '#ffffff');
  });

  it('paints the build menu from the game bar and gold selection', () => {
    assert.match(rule('.swl-build-menu'), /background:\s*var\(--swl-game-bar\)/);
    assert.match(rule('.swl-build-menu'), /border:\s*1px solid var\(--swl-ochre\)/);
    assert.match(rule('.swl-build-item button'), /color:\s*var\(--swl-game-ink\)/);
    assert.match(rule('.swl-build-item button:hover'), /background:\s*var\(--swl-game-bar-hover\)/);
    assert.match(rule('.swl-build-cost'), /color:\s*var\(--swl-game-label\)/);
    assert.match(rule('.swl-build-lock'), /color:\s*var\(--swl-ochre\)/);
    assert.match(rule('.swl-tab'), /color:\s*var\(--swl-game-label\)/);
  });

  it('paints the info panel from the game bar with readable ink', () => {
    assert.match(rule('.swl-info'), /background:\s*var\(--swl-game-bar\)/);
    assert.match(rule('.swl-info'), /border:\s*1px solid var\(--swl-ochre\)/);
    assert.match(rule('.swl-info-name'), /color:\s*var\(--swl-ochre\)/);
    assert.match(rule('.swl-info-earns'), /color:\s*var\(--swl-game-label\)/);
    assert.match(rule('.swl-info-stats dd'), /color:\s*var\(--swl-game-ink\)/);
    assert.match(rule('.swl-info-production'), /color:\s*var\(--swl-ochre\)/);
  });

  it('paints store items as gold-framed olive buttons', () => {
    assert.match(rule('.swl-store-item'), /border:\s*1px solid var\(--swl-ochre\)/);
    assert.match(rule('.swl-store-item'), /var\(--swl-olive\)/);
    assert.match(rule('.swl-store-item-name'), /color:\s*var\(--swl-game-ink\)/);
    assert.match(rule('.swl-ui button.swl-store-item-buy'), /var\(--swl-olive\)/);
  });

  it('paints quest accents from the gold and olive tokens', () => {
    assert.match(rule('.swl-quest-timer'), /color:\s*var\(--swl-ochre\)/);
    assert.match(rule('.swl-quest-star'), /color:\s*var\(--swl-ochre\)/);
    assert.match(rule('.swl-quest-counter dd'), /color:\s*var\(--swl-ochre\)/);
    assert.match(rule('.swl-quest-buttons .swl-quest-primary'), /background:\s*var\(--swl-game-bar\)/);
  });

  it('gives every contextual control a visible focus ring', () => {
    for (const selector of [
      '.swl-tab:focus-visible',
      '.swl-build-item button:focus-visible',
      '.swl-info-collect:focus-visible',
      '.swl-info-action-button:focus-visible',
      '.swl-info-period-button:focus-visible',
      '.swl-ui button.swl-store-item-buy:focus-visible',
      '.swl-quest-buttons button:focus-visible',
    ]) {
      assert.match(rule(selector), /outline:\s*2px solid var\(--swl-ochre\)/, selector);
    }
  });

  it('keeps the neighbour strip on the olive game bar', () => {
    assert.match(rule('.swl-neighbour'), /background:\s*var\(--swl-olive\)/);
    assert.match(rule('.swl-neighbour'), /border:\s*1px solid var\(--swl-ochre\)/);
  });
});

describe('contextual mounting stays unchanged', () => {
  it('keeps the at-rest surface list in the root byte-for-byte in order and count', () => {
    const start = root.indexOf('<div className="swl-ui">');
    const end = root.indexOf('<Dialog', start);
    assert.ok(start >= 0 && end > start, 'the root surface and the one dialog must exist');
    const atRest = [...root.slice(start, end).matchAll(/<([A-Z][A-Za-z0-9]*)/g)].map(
      (match) => match[1],
    );
    assert.deepEqual(atRest, [
      'Hud', 'Goals', 'Expansion', 'Inventory', 'Chapters',
      'InfoPanel', 'RecruitPanel', 'Store', 'MysteryLauncher',
      'SoulMixerLauncher', 'FusionLauncher', 'MagicLab', 'SpellBook',
      'Neighbours', 'OnboardingLauncher', 'OriginalArtLauncher',
      'OriginalFxLauncher', 'TutorialOverlay', 'Feedback', 'IconPanel',
      'ExtendedPortraitButton',
    ]);
  });

  it('keeps the contextual panels out of the at-rest chrome', () => {
    // The info panel is the only one of the four mounted before the dialog,
    // and it draws nothing until the player selects something.
    assert.match(info, /if \(!resource && !unit && !building\) return null;/);
    assert.equal((info.match(/className="swl-info"/g) ?? []).length, 1);
    assert.equal((neighbours.match(/className="swl-neighbours"/g) ?? []).length, 1);
    assert.equal((storeitems.match(/className="swl-store-items"/g) ?? []).length, 1);
    // Quest bodies are never top-level surfaces: all three live in the one
    // shared dialog, so the dialog's priority and z-order do not move.
    assert.equal((quests.match(/className="swl-quest-panel"/g) ?? []).length, 3);
    const dialogStart = root.indexOf('<Dialog');
    for (const name of ['QuestPanel', 'ProductionSelector']) {
      const at = root.indexOf(`<${name}`, dialogStart);
      assert.ok(at > dialogStart, `${name} must stay inside the shared dialog`);
    }
  });
});
