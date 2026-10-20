import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  CHAPTERS,
  CHAPTER_TITLES,
  MAX_QUESTS,
  QUESTS_PER_CHAPTER,
  chapterMap,
  chapters,
} from './chapters.ts';

describe('the chapter map', () => {
  it('has the client own shape', () => {
    assert.equal(MAX_QUESTS, 22);
    assert.equal(CHAPTERS, 4);
    assert.equal(QUESTS_PER_CHAPTER, 6);
  });

  it('has 24 slots, and the last two are empty', () => {
    const slots = chapterMap();
    assert.equal(slots.length, CHAPTERS * QUESTS_PER_CHAPTER);
    assert.equal(slots[MAX_QUESTS]!.index, MAX_QUESTS + 1);
    assert.equal(slots[MAX_QUESTS]!.locked, true);
  });

  it('starts with the first quest in progress and the rest locked', () => {
    const slots = chapterMap();
    assert.equal(slots[0]!.locked, false);
    assert.equal(slots[0]!.rank, 0);
    assert.equal(slots[1]!.locked, true);
  });

  it('opens the quests the player has reached', () => {
    const slots = chapterMap({ 1: 1, 2: 2, 3: 3 });
    assert.equal(slots[0]!.locked, false);
    assert.equal(slots[0]!.rank, 1);
    assert.equal(slots[1]!.rank, 2);
    assert.equal(slots[2]!.rank, 3);
    // The quest after the last ranked one is the one in progress.
    assert.equal(slots[3]!.locked, false);
    assert.equal(slots[3]!.rank, 0);
    // And the one after that is locked.
    assert.equal(slots[4]!.locked, true);
  });

  it('opens a quest out of order too', () => {
    // The client sends the ranks as it goes, and the server keeps them.
    //
    // The client's rule only advances "the first unranked quest" when it
    // finds a **ranked** one, so a quest ranked out of order is opened
    // and the quests between it and the first one stay locked.
    const slots = chapterMap({ 5: 1 });
    assert.equal(slots[4]!.locked, false);
    assert.equal(slots[4]!.rank, 1);
    // The first quest is the one in progress.
    assert.equal(slots[0]!.locked, false);
    assert.equal(slots[0]!.rank, 0);
    // And the quests between them are locked.
    assert.equal(slots[1]!.locked, true);
    assert.equal(slots[3]!.locked, true);
    // The quest after the last ranked one is open again.
    assert.equal(slots[5]!.locked, false);
  });

  it('never opens a quest the game does not have', () => {
    // The "first unranked quest" only moves on when a quest is **ranked**,
    // so with no ranks at all only the first quest is open - and the ones
    // after it stay locked until the player has done something.
    const slots = chapterMap({}, { numQuests: 3 });
    assert.equal(slots[0]!.locked, false);
    assert.equal(slots[1]!.locked, true);
    assert.equal(slots[2]!.locked, true);
  });

  it('opens the next quest once the one before it is ranked', () => {
    const slots = chapterMap({ 1: 1 }, { numQuests: 3 });
    assert.equal(slots[0]!.locked, false);
    assert.equal(slots[0]!.rank, 1);
    // The quest after the ranked one is the one in progress.
    assert.equal(slots[1]!.locked, false);
    assert.equal(slots[1]!.rank, 0);
    // And the one after that is not, because the game has three quests.
    assert.equal(slots[2]!.locked, true);
  });

  it('carries the level each quest unlocks at', () => {
    const slots = chapterMap({}, { minLevels: { 1: 0, 2: 5, 3: 12 } });
    assert.equal(slots[0]!.levelUnlock, 0);
    assert.equal(slots[1]!.levelUnlock, 5);
    assert.equal(slots[2]!.levelUnlock, 12);
    // The locked ones carry it too.
    assert.equal(slots[5]!.levelUnlock, 0);
  });
});

describe('the chapters', () => {
  it('are four, with six quests each', () => {
    const list = chapters(chapterMap());
    assert.equal(list.length, 4);
    for (const chapter of list) {
      assert.equal(chapter.quests.length, 6);
    }
  });

  it('have the client own titles', () => {
    const list = chapters(chapterMap());
    assert.equal(list[0]!.title, 'SMALL HARBOUR MISSIONS');
    assert.equal(list[1]!.title, 'HARBOUR MISSIONS');
    assert.equal(list[2]!.title, 'SPACE MISSIONS');
    // The client shares the third's title with the fourth.
    assert.equal(list[3]!.title, 'SPACE MISSIONS');
    assert.equal(CHAPTER_TITLES.length, 4);
  });

  it('hold the quests in order', () => {
    const list = chapters(chapterMap({ 1: 1 }));
    assert.equal(list[0]!.quests[0]!.index, 1);
    assert.equal(list[0]!.quests[5]!.index, 6);
    assert.equal(list[1]!.quests[0]!.index, 7);
    assert.equal(list[3]!.quests[5]!.index, 24);
  });
});
