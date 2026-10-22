import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import { Tutorial, tutorialLiteral, type TutorialStep } from './tutorial.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

async function steps(): Promise<TutorialStep[]> {
  const manifest = JSON.parse(
    await readFile(path.join(repoRoot(), 're/data/tutorial-steps.json'), 'utf8'),
  ) as { steps: TutorialStep[] };
  return manifest.steps;
}

describe('the tutorial steps', () => {
  it('were extracted from the client', async () => {
    const all = await steps();
    assert.ok(all.length >= 27, `only ${all.length} steps`);
    // The first step is the welcome.
    assert.equal(all[0]!.step, 100);
    // Most steps point somewhere; a few are the client's own popup steps
    // and have no pointer at all.
    const pointing = all.filter((step) => typeof step.x === 'number');
    assert.ok(pointing.length > all.length / 2, 'most steps should point somewhere');
    for (const step of pointing) {
      assert.equal(typeof step.y, 'number', `step ${step.step} has no pointer`);
    }
  });

  it('are the ones the client ships', async () => {
    const shipped = await readFile(
      path.join(repoRoot(), 'apps/client/public/tutorial-steps.json'),
      'utf8',
    );
    const extracted = await readFile(
      path.join(repoRoot(), 're/data/tutorial-steps.json'),
      'utf8',
    );
    // The client fetches the shipped copy, so a different one is a
    // tutorial the client draws from data nobody extracted.
    assert.deepEqual(JSON.parse(shipped), JSON.parse(extracted));
  });

  it('have the gated variant apart from the base list', async () => {
    const all = await steps();
    const gated = all.filter((step) => step.gate !== null);
    assert.equal(gated.length, 6);
    for (const step of gated) {
      assert.ok(step.gate!.includes('abVisitGeneralTutorial'));
    }
  });

  it('are in the client order, which is not the numeric order', async () => {
    const all = await steps();
    const numbers = all.map((step) => step.step);
    // The client's list interleaves the house-building steps with the goal
    // steps, so the numbers are not in order.
    const sorted = [...numbers].sort((a, b) => a - b);
    assert.notDeepEqual(numbers, sorted);
  });
});

describe('the tutorial', () => {
  it('shows the base list to a player with no variant', async () => {
    const all = await steps();
    const tutorial = new Tutorial(all);
    assert.equal(tutorial.length, all.length - 6);
    assert.equal(tutorial.current?.step, 100);
  });

  it('shows the gated steps to a player with the variant', async () => {
    const all = await steps();
    const tutorial = new Tutorial(all, { 'Base.Main.abVisitGeneralTutorial': true });
    assert.equal(tutorial.length, all.length);
  });

  it('advances and goes back', async () => {
    const all = await steps();
    const tutorial = new Tutorial(all);
    assert.equal(tutorial.current?.step, 100);
    tutorial.next();
    assert.equal(tutorial.current?.step, 101);
    tutorial.previous();
    assert.equal(tutorial.current?.step, 100);
  });

  it('does not go back past the first step', async () => {
    const all = await steps();
    const tutorial = new Tutorial(all);
    tutorial.previous();
    assert.equal(tutorial.position, 0);
  });

  it('finishes at the end', async () => {
    const all = await steps();
    const tutorial = new Tutorial(all);
    for (let index = 0; index < all.length + 2; index++) tutorial.next();
    assert.equal(tutorial.finished, true);
    assert.equal(tutorial.current, null);
  });

  it('skips only a step that allows it', async () => {
    const all = await steps();
    const tutorial = new Tutorial(all);
    // The welcome is skippable.
    assert.equal(tutorial.current?.skippable, true);
    assert.equal(tutorial.skip(), true);
    assert.equal(tutorial.finished, true);

    const other = new Tutorial(all);
    other.next();
    // The second step is not.
    assert.equal(other.current?.skippable, false);
    assert.equal(other.skip(), false);
    assert.equal(other.finished, false);
  });

  it('jumps to a step by its number', async () => {
    const all = await steps();
    const tutorial = new Tutorial(all);
    assert.equal(tutorial.jumpTo(108), true);
    assert.equal(tutorial.current?.step, 108);
    assert.equal(tutorial.jumpTo(9999), false);
  });

  it('compares the step by its number, as the client does', async () => {
    const all = await steps();
    const tutorial = new Tutorial(all);
    assert.equal(tutorial.isCurrent(100), true);
    tutorial.next();
    assert.equal(tutorial.isCurrent(100), false);
    assert.equal(tutorial.isCurrent(101), true);
  });

  it('resumes at the furthest step the server recorded', async () => {
    const all = await steps();
    const tutorial = new Tutorial(all);
    assert.equal(tutorial.jumpTo(108), true);
    assert.equal(tutorial.current?.step, 108);
    // A step the player has not reached in this variant is not in their
    // list, and the tutorial stays at the beginning rather than guessing.
    assert.equal(tutorial.jumpTo(134), false);
  });

  it('knows its last step, which is where it ends', async () => {
    const all = await steps();
    const tutorial = new Tutorial(all);
    assert.equal(tutorial.last?.step, 138);
    tutorial.finish();
    assert.equal(tutorial.finished, true);
  });
});

describe('the tutorial text', () => {
  it('reads the client literal', () => {
    assert.equal(
      tutorialLiteral('Language.getLiteral("WELCOME, SOLDIER!")'),
      'WELCOME, SOLDIER!',
    );
    assert.equal(
      tutorialLiteral('Language.getLiteral("Line one\\nLine two")'),
      'Line one\nLine two',
    );
    assert.equal(
      tutorialLiteral('Language.getLiteral("You\\\'ve been appointed")'),
      "You've been appointed",
    );
  });

  it('is empty when the client has no text', () => {
    assert.equal(tutorialLiteral(null), '');
    assert.equal(tutorialLiteral(undefined), '');
    assert.equal(tutorialLiteral('null'), '');
    assert.equal(tutorialLiteral(''), '');
  });

  it('is the client expression when it is not a literal', () => {
    assert.equal(tutorialLiteral('somethingElse'), 'somethingElse');
  });

  it('leaves no step truncated', async () => {
    const all = await steps();
    for (const step of all) {
      for (const field of ['title', 'lesson'] as const) {
        const value = step[field];
        if (typeof value !== 'string') continue;
        const text = tutorialLiteral(value);
        assert.ok(
          !text.includes('Language.getLiteral'),
          `step ${step.step}'s ${field} was not a complete literal: ${value}`,
        );
        // A literal that was cut at a comma has no closing quote and
        // parenthesis, and the parser hands it back as-is.
        assert.ok(
          value.endsWith(')') || value === 'null',
          `step ${step.step}'s ${field} was not complete: ${value}`,
        );
      }
    }
  });
});
