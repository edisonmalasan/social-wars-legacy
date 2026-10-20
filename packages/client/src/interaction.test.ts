import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { Interaction } from './interaction.ts';

describe('the selection', () => {
  it('starts with nothing selected', () => {
    const interaction = new Interaction();
    assert.equal(interaction.selection.kind, 'none');
  });

  it('selects an element', () => {
    const interaction = new Interaction();
    const selection = interaction.selectElement(7, 1007, 'unit');
    assert.equal(selection.kind, 'element');
    assert.equal(interaction.selection.kind, 'element');
  });

  it('begins a placement', () => {
    const interaction = new Interaction();
    interaction.beginPlacement(30, 'b');
    assert.equal(interaction.selection.kind, 'placement');
  });

  it('clears the selection', () => {
    const interaction = new Interaction();
    interaction.selectElement(7, 1007, 'unit');
    interaction.clear();
    assert.equal(interaction.selection.kind, 'none');
  });
});

describe('the gestures', () => {
  it('move the selected element', () => {
    const interaction = new Interaction();
    interaction.selectElement(7, 1007, 'unit');
    const gesture = interaction.moveTo(4, 5);
    assert.equal(gesture.ok, true);
    if (!gesture.ok) return;
    assert.equal(gesture.command.name, 'move');
    assert.equal(gesture.command.args[0], 7);
    assert.equal(gesture.command.args[1], 4);
    assert.equal(gesture.command.args[2], 5);
  });

  it('refuse to move a building that is still being built', () => {
    const interaction = new Interaction();
    interaction.selectElement(7, 30, 'building', true);
    const gesture = interaction.moveTo(4, 5);
    assert.equal(gesture.ok, false);
    if (gesture.ok) return;
    assert.equal(gesture.refusal, 'under-construction');
  });

  it('refuse a gesture with nothing selected', () => {
    const interaction = new Interaction();
    for (const gesture of [
      interaction.moveTo(1, 1),
      interaction.placeTo(1, 1),
      interaction.collectSelected(),
      interaction.trainSelected(),
      interaction.upgradeSelected(),
    ]) {
      assert.equal(gesture.ok, false);
      if (gesture.ok) continue;
      assert.equal(gesture.refusal, 'nothing-selected');
    }
  });

  it('place a stored building', () => {
    const interaction = new Interaction();
    interaction.beginPlacement(30, 'b');
    const gesture = interaction.placeTo(2, 3, true);
    assert.equal(gesture.ok, true);
    if (!gesture.ok) return;
    assert.equal(gesture.command.name, 'place_stored_item');
  });

  it('buy a building that is not in the store', () => {
    const interaction = new Interaction();
    interaction.beginPlacement(30, 'b');
    const gesture = interaction.placeTo(2, 3, false);
    assert.equal(gesture.ok, true);
    if (!gesture.ok) return;
    assert.equal(gesture.command.name, 'buy');
    assert.equal(gesture.command.args[1], 30);
  });

  it('collect the selected building', () => {
    const interaction = new Interaction();
    interaction.selectElement(7, 2, 'building');
    const gesture = interaction.collectSelected();
    assert.equal(gesture.ok, true);
    if (!gesture.ok) return;
    assert.equal(gesture.command.name, 'collect');
  });

  it('train in the selected building', () => {
    const interaction = new Interaction();
    interaction.selectElement(7, 30, 'building');
    const gesture = interaction.trainSelected(1007);
    assert.equal(gesture.ok, true);
    if (!gesture.ok) return;
    assert.equal(gesture.command.name, 'push_queue_unit2');
    assert.equal(gesture.command.args[1], 1007);
  });

  it('train without naming a unit', () => {
    const interaction = new Interaction();
    interaction.selectElement(7, 30, 'building');
    const gesture = interaction.trainSelected();
    assert.equal(gesture.ok, true);
    if (!gesture.ok) return;
    assert.equal(gesture.command.name, 'push_queue_unit');
  });

  it('upgrade the selected building', () => {
    const interaction = new Interaction();
    interaction.selectElement(7, 30, 'building');
    const gesture = interaction.upgradeSelected();
    assert.equal(gesture.ok, true);
    if (!gesture.ok) return;
    assert.equal(gesture.command.name, 'upgrade');
  });

  it('refuse to upgrade a unit', () => {
    const interaction = new Interaction();
    interaction.selectElement(7, 1007, 'unit');
    const gesture = interaction.upgradeSelected();
    assert.equal(gesture.ok, false);
  });
});
