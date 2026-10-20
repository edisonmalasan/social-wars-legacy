import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  MAP_WIDTH,
  TILE_HEIGHT_PIXELS,
  TILE_WIDTH_PIXELS,
  compareDepth,
  sortByDepth,
  tileToPixel,
  zIndex,
  type Drawable,
  type Viewport,
} from './iso.ts';

/**
 * The depth sort and the projection, checked against the client's own code.
 *
 * The formulas below are **transcriptions** of the decompiled ActionScript,
 * written out again here rather than imported, so that a change to the
 * clone's port cannot quietly change the answer: the two are compared over
 * a grid, not just at a few points.
 *
 * ## The client's depth
 *
 * ```as3
 * // core/Utils.as:398-409
 * public static function assignZIndex(param1:BuildingReference) : void {
 *    var _loc2_:Number = 20000
 *      + Config.EI_MAP_WIDTH * param1.tx
 *      + param1.ty * Config.EI_MAP_WIDTH
 *      - param1.building.width * Config.EI_MAP_WIDTH;
 *    if (param1.building != null) {
 *       if (Base.Properties.elementHasProperty(param1.building.id, PropertyManager.WALKABLE)) {
 *          _loc2_ -= 20000;
 *       }
 *    }
 *    param1.zIndex = _loc2_;
 * }
 * ```
 *
 * ## The client's projection
 *
 * ```as3
 * // core/Utils.as:88-102
 * public static function TileToPixel(param1:Number, param2:Number) : Object {
 *    var _loc3_:int = Base.Main.topX - 54 * param2 + 54 * param1;
 *    var _loc4_:int = Base.Main.topY - Base.Main.offsetBuildOutlineY
 *      + 27 * param2 + 27 * param1;
 *    return { "x":_loc3_, "y":_loc4_ - 27 };
 * }
 * ```
 */

/** The client's `Utils.assignZIndex`, transcribed. */
function clientZIndex(
  tx: number,
  ty: number,
  width: number,
  walkable: boolean,
): number {
  let index = 20000 + 100 * tx + ty * 100 - width * 100;
  if (walkable) index -= 20000;
  return index;
}

/** The client's `Utils.TileToPixel`, transcribed. */
function clientTileToPixel(
  tx: number,
  ty: number,
  topX: number,
  topY: number,
  offsetBuildOutlineY: number,
): { x: number; y: number } {
  const x = topX - 54 * ty + 54 * tx;
  const y = topY - offsetBuildOutlineY + 27 * ty + 27 * tx;
  return { x, y: y - 27 };
}

describe('the depth matches the client', () => {
  it('is the client formula over the whole map', () => {
    for (let tx = 0; tx < 100; tx += 7) {
      for (let ty = 0; ty < 100; ty += 11) {
        for (const width of [1, 2, 3, 4]) {
          for (const walkable of [false, true]) {
            assert.equal(
              zIndex(tx, ty, width, walkable),
              clientZIndex(tx, ty, width, walkable),
              `zIndex(${tx}, ${ty}, ${width}, ${walkable})`,
            );
          }
        }
      }
    }
  });

  it('is the client formula at the map edges', () => {
    for (const [tx, ty] of [
      [0, 0],
      [99, 0],
      [0, 99],
      [99, 99],
      [50, 50],
    ] as [number, number][]) {
      assert.equal(
        zIndex(tx, ty, 1, false),
        clientZIndex(tx, ty, 1, false),
        `zIndex(${tx}, ${ty})`,
      );
    }
  });
});

describe('the projection matches the client', () => {
  const viewport: Viewport = { topX: 300, topY: 200, buildOutlineOffsetY: 54 };

  it('is the client formula over the whole map', () => {
    for (let tx = 0; tx < 100; tx += 7) {
      for (let ty = 0; ty < 100; ty += 11) {
        const actual = tileToPixel(tx, ty, viewport);
        const expected = clientTileToPixel(tx, ty, viewport.topX, viewport.topY, 54);
        assert.equal(actual.x, expected.x, `x at (${tx}, ${ty})`);
        assert.equal(actual.y, expected.y, `y at (${tx}, ${ty})`);
      }
    }
  });

  it('uses the client tile metrics', () => {
    assert.equal(TILE_WIDTH_PIXELS, 108);
    assert.equal(TILE_HEIGHT_PIXELS, 54);
    assert.equal(MAP_WIDTH, 100);
  });
});

describe('the occlusion', () => {
  function element(
    tx: number,
    ty: number,
    over: Partial<Drawable> = {},
  ): Drawable {
    return { tx, ty, width: 1, walkable: false, ...over };
  }

  it('puts the element in front last', () => {
    // Further down the map is further towards the viewer.
    const behind = element(10, 10);
    const inFront = element(10, 11);
    assert.ok(compareDepth(behind, inFront) < 0);
    assert.ok(compareDepth(inFront, behind) > 0);
  });

  it('puts the element to the right last', () => {
    const behind = element(10, 10);
    const inFront = element(11, 10);
    assert.ok(compareDepth(behind, inFront) < 0);
  });

  it('puts a wide element behind a narrow one further up the map', () => {
    // The width shifts the element back by its own width, so a wide
    // building's art is drawn behind a narrow one that stands further up
    // the map. The wide one is at row 12 and the narrow one at row 11, and
    // the wide one's four tiles of width put it back three rows' worth -
    // far enough to be behind the narrow one.
    const wide = element(10, 12, { width: 4 });
    const narrow = element(10, 11, { width: 1 });
    assert.ok(compareDepth(wide, narrow) < 0);
  });

  it('puts a wide element behind a narrow one at the same tile', () => {
    // At the same tile the width is the only difference, and it puts the
    // wide building behind the narrow one.
    const wide = element(10, 12, { width: 4 });
    const narrow = element(10, 12, { width: 1 });
    assert.ok(compareDepth(wide, narrow) < 0);
  });

  it('puts a walkable element behind everything', () => {
    const road = element(10, 10, { walkable: true });
    const building = element(10, 10);
    assert.ok(compareDepth(road, building) < 0);
    // Even against the last element on the map.
    const far = element(99, 99);
    assert.ok(compareDepth(road, far) < 0);
  });

  it('sorts a map into the order the client draws it', () => {
    const map = [
      element(12, 12),
      element(10, 10, { walkable: true }),
      element(11, 11),
      element(10, 10),
      element(10, 12, { width: 4 }),
    ];
    const sorted = sortByDepth(map);
    // The road is behind everything, and the wide building is behind the
    // narrow one further up the map.
    assert.equal(sorted[0]!.walkable, true);
    assert.equal(sorted[1]!.width, 4);
    assert.equal(sorted[1]!.ty, 12);
    assert.equal(sorted[2]!.tx, 10);
    assert.equal(sorted[2]!.ty, 10);
    assert.equal(sorted[3]!.tx, 11);
    assert.equal(sorted[4]!.tx, 12);
  });
});
