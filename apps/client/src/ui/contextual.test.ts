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

/** The component tags rendered by a slice of JSX, in source order. */
function components(block: string): string[] {
  return [...block.matchAll(/<([A-Z][A-Za-z0-9]*)/g)].map((match) => match[1]!);
}

/** The one-surface focus wrapper added by the merged active-surface lane. */
const WRAPPER = "<div style={{ position: 'absolute', left: 0, right: 0, top: 0, bottom: 48 }}>";

describe('contextual mounting stays unchanged', () => {
  it('keeps only the HUD, neighbours and feedback at rest — no panel is unguarded', () => {
    const rootStart = root.indexOf('<div className="swl-ui">');
    const dialogStart = root.indexOf('<Dialog', rootStart);
    const wrapperStart = root.indexOf(WRAPPER, rootStart);
    assert.ok(rootStart >= 0 && wrapperStart > rootStart && dialogStart > wrapperStart,
      'the root, its one focus wrapper and the one dialog must exist');
    const wrapperInner = wrapperStart + WRAPPER.length;
    const wrapperEnd = root.indexOf('</div>', wrapperInner);
    assert.ok(wrapperEnd > wrapperInner && wrapperEnd < dialogStart,
      'the focus wrapper must close before the dialog');

    // Outside the wrapper nothing but the HUD, the at-rest neighbour strip and
    // the two transient channels is mounted. A new at-rest panel would add a
    // component here and fail this exact list.
    assert.deepEqual(components(root.slice(rootStart, wrapperInner)), ['Hud', 'Neighbours']);
    assert.deepEqual(components(root.slice(wrapperEnd, dialogStart)), [
      'TutorialOverlay', 'Feedback',
    ]);

    // Inside the wrapper every panel is one of the twelve gated surfaces, in
    // the order the nav declares them. The order and the count are the point:
    // one active surface, never a stack of at-rest panels.
    assert.deepEqual(components(root.slice(wrapperInner, wrapperEnd)), [
      'Goals', 'Expansion', 'Inventory', 'Chapters', 'InfoPanel', 'RecruitPanel',
      'Store', 'MysteryLauncher', 'SoulMixerLauncher', 'FusionLauncher',
      'OnboardingLauncher', 'OriginalArtLauncher', 'OriginalFxLauncher',
      'IconPanel', 'ExtendedPortraitButton', 'MagicLab', 'SpellBook',
      'BuildMenu', 'ChromeDock',
    ]);

    // The neighbour strip is the only panel allowed when no surface is open;
    // the bottom nav is the only other at-rest control.
    assert.match(root, /surface\.surface === 'none' \? <Neighbours\b/);
    assert.match(root, /<nav\s+className="swl-surface-nav"/);
  });

  it('mounts each contextual panel only for its own active surface', () => {
    const gates: readonly (readonly [string, string])[] = [
      ['goals', 'Goals'],
      ['expansion', 'Expansion'],
      ['inventory', 'Inventory'],
      ['chapters', 'Chapters'],
      ['info', 'InfoPanel'],
      ['recruit', 'RecruitPanel'],
      ['store', 'Store'],
      ['launchers', 'MysteryLauncher'],
      ['magiclab', 'MagicLab'],
      ['spellbook', 'SpellBook'],
      ['build', 'BuildMenu'],
      ['controls', 'ChromeDock'],
    ];
    for (const [id, component] of gates) {
      const gate = new RegExp(
        `surface\\.surface === '${id}' \\?[\\s\\S]{0,240}?<${component}\\b`,
      );
      assert.match(root, gate, `${component} must be mounted only for '${id}'`);
    }

    // The four repainted panels keep a single surface root each, and the info
    // panel still draws nothing on its own when there is no selection.
    assert.match(info, /if \(!resource && !unit && !building\) return null;/);
    assert.equal((info.match(/className="swl-info"/g) ?? []).length, 1);
    assert.equal((neighbours.match(/className="swl-neighbours"/g) ?? []).length, 1);
    assert.equal((storeitems.match(/className="swl-store-items"/g) ?? []).length, 1);

    // Quest bodies are never top-level surfaces: all three stay in the one
    // shared dialog, so its priority and z-order do not move.
    assert.equal((quests.match(/className="swl-quest-panel"/g) ?? []).length, 3);
    const dialogStart = root.indexOf('<Dialog');
    for (const name of ['QuestPanel', 'ProductionSelector']) {
      const at = root.indexOf(`<${name}`, dialogStart);
      assert.ok(at > dialogStart, `${name} must stay inside the shared dialog`);
    }
  });
});
