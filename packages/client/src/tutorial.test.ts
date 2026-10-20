import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import { Tutorial, type TutorialStep } from './tutorial.ts';

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
});
