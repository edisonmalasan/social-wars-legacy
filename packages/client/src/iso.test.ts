import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  MAP_HEIGHT,
  MAP_WIDTH,
  TILE_HEIGHT_PIXELS,
  TILE_WIDTH_PIXELS,
  compareDepth,
  depthOf,
  isOnMap,
  pixelToTile,
  sortByDepth,
  tileToPixel,
  zIndex,
  type Drawable,
} from './iso.ts';

/** The viewport the client's own tests would use: the map's origin. */
const VIEWPORT = { topX: 0, topY: 0 };

describe('the tile constants', () => {
  it('are the client own', () => {
    // Config.EI_TILE_WIDTH_PIXELS, EI_TILE_HEIGHT_PIXELS, EI_MAP_WIDTH,
    // EI_MAP_HEIGHT.
    assert.equal(TILE_WIDTH_PIXELS, 108);
    assert.equal(TILE_HEIGHT_PIXELS, 54);
    assert.equal(MAP_WIDTH, 100);
    assert.equal(MAP_HEIGHT, 100);
  });
});

describe('the projection', () => {
  it('puts the origin at the top corner of the first tile', () => {
    const point = tileToPixel(0, 0, VIEWPORT);
    assert.equal(point.x, 0);
    // The origin is half a tile above the tile's centre.
    assert.equal(point.y, -TILE_HEIGHT_PIXELS / 2);
  });

  it('moves right along one axis and up along the other', () => {
    // One tile east: right by a tile's width, down by half its height.
    const east = tileToPixel(1, 0, VIEWPORT);
    assert.equal(east.x, TILE_HEIGHT_PIXELS);
    assert.equal(east.y, 0);

    // One tile south: left by a tile's width, down by half its height.
    const south = tileToPixel(0, 1, VIEWPORT);
    assert.equal(south.x, -TILE_HEIGHT_PIXELS);
    assert.equal(south.y, 0);
  });

  it('follows the viewport', () => {
    const viewport = { topX: 500, topY: 300 };
    const point = tileToPixel(3, 4, viewport);
    assert.equal(point.x, 500 + TILE_HEIGHT_PIXELS * 3 - TILE_HEIGHT_PIXELS * 4);
    assert.equal(point.y, 300 + (TILE_HEIGHT_PIXELS / 2) * 4 + (TILE_HEIGHT_PIXELS / 2) * 3 - 27);
  });

  it('round-trips through the inverse', () => {
    // The client's inverse is calibrated to the tile's TOP CORNER, which is
    // what `tileToPixel` returns - not to the centre of the diamond.
    // Feeding it the centre instead is off by one tile on both axes.
    const tiles: readonly (readonly [number, number])[] = [
      [0, 0],
      [1, 0],
      [0, 1],
      [1, 1],
      [7, 13],
      [99, 99],
    ];
    for (const [tx, ty] of tiles) {
      const point = tileToPixel(tx, ty, VIEWPORT);
      const back = pixelToTile(point.x, point.y, VIEWPORT);
      assert.equal(back.tx, tx, `tx for ${tx},${ty}`);
      assert.equal(back.ty, ty, `ty for ${tx},${ty}`);
    }
  });

  it('is off by one when given the centre of a tile', () => {
    // This is the client's own behaviour, and it is worth knowing: the two
    // functions are only inverses of each other at the top corner.
    const point = tileToPixel(0, 0, VIEWPORT);
    const centre = { x: point.x, y: point.y + TILE_HEIGHT_PIXELS / 2 };
    const back = pixelToTile(centre.x, centre.y, VIEWPORT);
    assert.equal(back.tx, 1);
    assert.equal(back.ty, 1);
  });

  it('inverts a shifted viewport too', () => {
    const viewport = { topX: 640, topY: 480 };
    const point = tileToPixel(11, 23, viewport);
    const back = pixelToTile(point.x, point.y, viewport);
    assert.equal(back.tx, 11);
    assert.equal(back.ty, 23);
  });
});

describe('the depth sort', () => {
  it('puts a tile further along the row in front', () => {
    assert.ok(zIndex(5, 5, 1, false) < zIndex(6, 5, 1, false));
    assert.ok(zIndex(5, 5, 1, false) < zIndex(5, 6, 1, false));
  });

  it('shifts a wide building back', () => {
    // A building three tiles wide is drawn behind a narrow one on the
    // next tile up.
    assert.ok(zIndex(5, 6, 3, false) < zIndex(5, 5, 1, false));
  });

  it('puts a walkable building behind everything', () => {
    const walkable = zIndex(0, 0, 1, true);
    const ordinary = zIndex(0, 0, 1, false);
    assert.ok(walkable < ordinary);
    // And behind a building at the map's very first tile.
    assert.ok(walkable < zIndex(0, 1, 1, false));
  });

  it('keeps the walkable building on the map', () => {
    // The offset cancels out, so a walkable building's index is still a
    // sensible tile index rather than a huge negative number.
    assert.equal(zIndex(3, 4, 1, true), MAP_WIDTH * 3 + 4 * MAP_WIDTH - MAP_WIDTH);
  });

  it('sorts a list into drawing order', () => {
    const drawables: Drawable[] = [
      { tx: 5, ty: 5, width: 1, walkable: false },
      { tx: 1, ty: 1, width: 1, walkable: false },
      { tx: 3, ty: 3, width: 1, walkable: true },
      { tx: 2, ty: 2, width: 1, walkable: false },
    ];
    const sorted = sortByDepth(drawables);
    // The walkable one is first, then the tiles in order.
    assert.equal(sorted[0]!.walkable, true);
    assert.deepEqual(
      sorted.map((d) => [d.tx, d.ty]),
      [
        [3, 3],
        [1, 1],
        [2, 2],
        [5, 5],
      ],
    );
  });

  it('does not modify the list it is given', () => {
    const drawables: Drawable[] = [
      { tx: 5, ty: 5, width: 1, walkable: false },
      { tx: 1, ty: 1, width: 1, walkable: false },
    ];
    sortByDepth(drawables);
    assert.equal(drawables[0]!.tx, 5);
  });

  it('is stable for equal depths', () => {
    // Two elements on the same tile with the same width must keep their
    // order, or they would flicker between frames.
    const a: Drawable = { tx: 4, ty: 4, width: 1, walkable: false };
    const b: Drawable = { tx: 4, ty: 4, width: 1, walkable: false };
    const sorted = sortByDepth([a, b]);
    assert.equal(sorted[0], a);
    assert.equal(sorted[1], b);
    assert.equal(compareDepth(a, b), 0);
  });

  it('computes a drawable depth the same way', () => {
    const drawable: Drawable = { tx: 7, ty: 8, width: 2, walkable: false };
    assert.equal(depthOf(drawable), zIndex(7, 8, 2, false));
  });
});

describe('the map bounds', () => {
  it('accepts a tile on the map', () => {
    assert.equal(isOnMap(0, 0), true);
    assert.equal(isOnMap(99, 99), true);
  });

  it('refuses a tile off the map', () => {
    assert.equal(isOnMap(-1, 0), false);
    assert.equal(isOnMap(0, -1), false);
    assert.equal(isOnMap(100, 0), false);
    assert.equal(isOnMap(0, 100), false);
  });
});
