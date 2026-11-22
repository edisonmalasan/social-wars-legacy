/**
 * Original, provenance-verified **gameplay** art.
 *
 * The Foundry icons and the FX frames in this package are gallery pieces. This
 * module is the first set of motifs a renderer can use for the actual game:
 * town terrain, building families, units, selection markers and combat impact.
 *
 * Everything here is deterministic and clean-room. Geometry comes from integer
 * coordinate tables, the seeded stream in `random.ts` and the primitives in
 * `svg.ts`. No image, sprite source, decompiled client or configuration file
 * is read.
 *
 * Crucially, a motif is chosen **only from neutral content properties**: the
 * item's `type` (`'b'` or `'u'`), its `groupType`, its numeric category and
 * subcategory, or a caller-supplied neutral key. There is deliberately no way
 * to pass a graphic's name, a symbol identifier or any other art-derived
 * string. That keeps the mapping a statement about *what an item is*, not
 * about what somebody else drew.
 */
import { makeRandom, seedFor, type Random } from './random.ts';
import {
  PALETTE,
  circle,
  ellipse,
  escapeXml,
  group,
  line,
  n,
  path,
  polygon,
  rect,
  type Point,
} from './svg.ts';

/** Canonical, stable keys. These are the public vocabulary of this module. */
export type GameplayCategory =
  | 'terrain.grass'
  | 'terrain.water'
  | 'terrain.path'
  | 'terrain.stone'
  | 'building.housing'
  | 'building.workshop'
  | 'building.farm'
  | 'building.storage'
  | 'building.tower'
  | 'unit.infantry'
  | 'unit.ranged'
  | 'unit.mounted'
  | 'unit.worker'
  | 'marker.selection'
  | 'marker.highlight'
  | 'fx.impact'
  | 'fallback';

/** The key used whenever a caller supplies nothing recognisable. */
export const GAMEPLAY_FALLBACK_KEY = 'fallback';

/** The only properties a caller may use to choose a motif. */
export interface GameplayContentProps {
  /** The content's neutral item type: `'b'` for a building, `'u'` for a unit. */
  readonly type?: string;
  /** The content's neutral group classification, e.g. `HOUSING` or `WOOD_FACTORY`. */
  readonly groupType?: string;
  /** The content's numeric category. */
  readonly categoryId?: number;
  /** The content's numeric subcategory. */
  readonly subcategoryId?: number;
  /** A neutral key supplied by the caller, e.g. `'terrain.grass'` or `'housing'`. */
  readonly key?: string;
}

/** One motif: its identity, its geometry and its rendering contract. */
export interface GameplayCategorySpec {
  readonly key: GameplayCategory;
  readonly title: string;
  readonly description: string;
  readonly kind: 'terrain' | 'building' | 'unit' | 'marker' | 'fx' | 'fallback';
  /** The intrinsic, positive canvas size in SVG user units. */
  readonly width: number;
  readonly height: number;
  /** Terrain tiles repeat; every other motif has a transparent background. */
  readonly tileable: boolean;
  /** The opaque base colour of a tileable motif. */
  readonly background?: string;
  draw(random: Random): string;
}

const TILE = 64;

/** A circle drawn as an outline rather than a filled disc. */
function ring(cx: number, cy: number, r: number, stroke: string, width: number, dash = ''): string {
  const dashPart = dash ? ` stroke-dasharray="${escapeXml(dash)}"` : '';
  return `    <circle cx="${n(cx)}" cy="${n(cy)}" r="${n(r)}" fill="none" stroke="${stroke}" stroke-width="${n(width)}"${dashPart}/>\n`;
}

/** A polygon drawn as an outline rather than a filled shape. */
function outline(points: readonly Point[], stroke: string, width: number, dash = ''): string {
  const list = points.map(([x, y]) => `${n(x)},${n(y)}`).join(' ');
  const dashPart = dash ? ` stroke-dasharray="${escapeXml(dash)}"` : '';
  return `    <polygon points="${list}" fill="none" stroke="${stroke}" stroke-width="${n(width)}" stroke-linejoin="round"${dashPart}/>\n`;
}

/** Repeat a tile's body over the eight neighbours so its edges always meet. */
function wrapTile(body: string, width: number, height: number): string {
  let out = '';
  for (const dy of [-height, 0, height]) {
    for (const dx of [-width, 0, width]) {
      out += group(body, `translate(${dx} ${dy})`);
    }
  }
  return out;
}

/** Four short blades of grass at a fixed offset. */
function tuft(x: number, y: number, tone: string): string {
  return (
    line(x - 3, y, x - 4, y - 7, tone, 1.5) +
    line(x, y, x, y - 10, tone, 1.5) +
    line(x + 3, y, x + 4, y - 6, tone, 1.5)
  );
}

function drawGrass(r: Random): string {
  let body = '';
  const blades = r.int(3, 5);
  for (let i = 0; i < blades; i += 1) {
    body += tuft(8 + i * 11, 20 + (i % 3) * 15, i % 2 === 0 ? '#568952' : '#6da05c');
  }
  body += circle(30, 44, 1.5, '#a9c98a') + circle(52, 12, 1.5, '#a9c98a');
  return body;
}

function drawWater(r: Random): string {
  const glints = r.int(2, 4);
  let body = path('M4 18 Q16 12 28 18 T52 18', 'none', '#5d9bb0', 2);
  body += path('M12 40 Q24 34 36 40 T60 40', 'none', '#5d9bb0', 2);
  body += path('M-8 57 Q4 51 16 57 T40 57', 'none', '#5d9bb0', 2);
  for (let i = 0; i < glints; i += 1) {
    body += line(8 + i * 14, 27 + (i % 2) * 12, 16 + i * 14, 27 + (i % 2) * 12, '#b7dde3', 1.5);
  }
  return body;
}

function drawPath(r: Random): string {
  let body = rect(0, 22, TILE, 22, '#8a7c5a');
  body += rect(0, 24, TILE, 2, '#a99a72') + rect(0, 40, TILE, 2, '#6d6147');
  const pebbles = r.int(3, 5);
  for (let i = 0; i < pebbles; i += 1) {
    const x = 6 + i * 12;
    body += ellipse(x, 30 + (i % 2) * 7, 3, 1.6, i % 2 === 0 ? '#c1b18a' : '#5f5540');
  }
  return body;
}

function drawStone(r: Random): string {
  let body = polygon([[0, 0], [26, 0], [18, 16], [0, 22]], '#707781');
  body += polygon([[64, 8], [64, 38], [45, 30], [40, 14]], '#666d77');
  body += polygon([[0, 48], [22, 40], [38, 64], [0, 64]], '#7c838c');
  const chips = r.int(2, 4);
  for (let i = 0; i < chips; i += 1) {
    const x = 28 + i * 10;
    body += line(x, 22 + (i % 2) * 10, x + 5, 26 + (i % 2) * 10, '#9aa1a9', 1.5);
  }
  return body;
}

function drawHousing(r: Random): string {
  const windows = r.int(1, 3);
  let body = polygon([[8, 30], [32, 10], [56, 30]], PALETTE.rust);
  body += rect(12, 30, 40, 25, PALETTE.cream);
  body += rect(40, 14, 7, 11, PALETTE.slate);
  body += rect(27, 39, 10, 16, PALETTE.slate, 1);
  body += circle(34, 47, 1.3, PALETTE.amber);
  for (let i = 0; i < windows; i += 1) {
    body += rect(15 + i * 7, 35, 5, 6, PALETTE.teal, 1);
  }
  return body;
}

function drawWorkshop(r: Random): string {
  const logs = r.int(2, 4);
  let body = polygon([[7, 30], [32, 14], [57, 30]], PALETTE.slate);
  body += rect(11, 30, 42, 24, PALETTE.amber);
  for (let i = 0; i < logs; i += 1) {
    body += rect(6 + i * 7, 48 - i * 4, 16, 5, PALETTE.rust, 2);
  }
  body += ring(47, 20, 6, PALETTE.ink, 2);
  body += line(47, 11, 47, 29, PALETTE.cream, 1.5);
  body += line(38, 20, 56, 20, PALETTE.cream, 1.5);
  return body;
}

function drawFarm(r: Random): string {
  const furrows = r.int(3, 5);
  let body = rect(6, 40, 52, 16, '#765f3f');
  for (let i = 0; i < furrows; i += 1) {
    body += line(9, 43 + i * 3, 55, 43 + i * 3, '#a58855', 1.5);
  }
  body += polygon([[12, 38], [32, 20], [52, 38]], PALETTE.rust);
  body += rect(16, 38, 32, 12, PALETTE.cream);
  body += rect(28, 42, 8, 8, PALETTE.slate, 1);
  return body;
}

function drawStorage(r: Random): string {
  const crates = r.int(2, 4);
  let body = rect(9, 22, 46, 32, PALETTE.slate);
  body += polygon([[9, 22], [32, 9], [55, 22]], PALETTE.amber);
  body += rect(25, 36, 14, 18, PALETTE.rust, 1);
  body += line(32, 36, 32, 54, PALETTE.cream, 1.5);
  for (let i = 0; i < crates; i += 1) {
    body += rect(12 + i * 11, 28, 9, 9, PALETTE.cream, 1);
  }
  return body;
}

function drawTower(r: Random): string {
  const merlons = r.int(2, 4);
  let body = rect(15, 22, 34, 34, PALETTE.slate);
  body += rect(11, 16, 42, 8, PALETTE.teal);
  for (let i = 0; i < merlons; i += 1) {
    body += rect(12 + i * 11, 10, 7, 8, PALETTE.cream, 1);
  }
  body += rect(29, 36, 6, 20, PALETTE.ink, 2);
  body += rect(30, 12, 3, 12, PALETTE.rust, 1);
  body += polygon([[33, 13], [45, 16], [33, 20]], PALETTE.amber);
  return body;
}

function drawInfantry(r: Random): string {
  const studs = r.int(1, 3);
  let body = circle(32, 14, 7, PALETTE.cream);
  body += rect(26, 21, 12, 23, PALETTE.teal, 3);
  body += rect(20, 41, 8, 15, PALETTE.slate, 2) + rect(36, 41, 8, 15, PALETTE.slate, 2);
  body += polygon([[14, 24], [28, 24], [26, 42], [14, 38]], PALETTE.amber);
  body += line(44, 20, 44, 48, PALETTE.cream, 3);
  body += rect(41, 17, 6, 4, PALETTE.slate, 1);
  for (let i = 0; i < studs; i += 1) {
    body += circle(18 + i * 4, 30, 1.3, PALETTE.ink);
  }
  return body;
}

function drawRanged(r: Random): string {
  const arrows = r.int(2, 4);
  let body = circle(28, 14, 7, PALETTE.cream);
  body += rect(23, 21, 11, 22, PALETTE.rust, 3);
  body += rect(19, 41, 7, 14, PALETTE.slate, 2) + rect(32, 41, 7, 14, PALETTE.slate, 2);
  body += path('M44 14 Q57 32 44 50', 'none', PALETTE.amber, 3);
  body += line(44, 14, 44, 50, PALETTE.cream, 1);
  for (let i = 0; i < arrows; i += 1) {
    const x = 12 + i * 4;
    body += line(x, 48, x - 4, 28, PALETTE.slate, 1.5);
    body += polygon([[x - 4, 28], [x - 6, 32], [x - 2, 32]], PALETTE.aqua);
  }
  return body;
}

function drawMounted(r: Random): string {
  const mane = r.int(1, 3);
  let body = polygon([[10, 40], [24, 28], [46, 28], [56, 38], [50, 48], [18, 48]], PALETTE.slate);
  body += polygon([[46, 28], [58, 18], [60, 28], [52, 34]], PALETTE.slate);
  body += line(16, 48, 14, 58, PALETTE.ink, 3) + line(46, 48, 48, 58, PALETTE.ink, 3);
  body += circle(34, 18, 6, PALETTE.cream);
  body += rect(29, 24, 10, 14, PALETTE.rust, 2);
  body += line(40, 26, 50, 20, PALETTE.ink, 2);
  for (let i = 0; i < mane; i += 1) {
    body += line(48 + i * 2, 20, 54 + i * 2, 16, PALETTE.amber, 1.5);
  }
  return body;
}

function drawWorker(r: Random): string {
  const sparks = r.int(1, 3);
  let body = circle(24, 15, 7, PALETTE.cream);
  body += rect(19, 22, 11, 21, PALETTE.amber, 3);
  body += rect(15, 41, 7, 14, PALETTE.slate, 2) + rect(28, 41, 7, 14, PALETTE.slate, 2);
  body += line(33, 44, 51, 22, PALETTE.rust, 4);
  body += path('M36 18 Q45 10 54 18', 'none', PALETTE.slate, 5);
  body += rect(40, 50, 16, 10, PALETTE.cream, 1);
  for (let i = 0; i < sparks; i += 1) {
    body += circle(50 + i * 3, 26 - i * 4, 1.5, PALETTE.aqua);
  }
  return body;
}

function drawSelection(r: Random): string {
  const dashes = r.int(4, 6);
  const pattern = `${dashes} ${dashes - 2}`;
  let body = outline([[32, 6], [58, 32], [32, 58], [6, 32]], PALETTE.amber, 3, pattern);
  for (const [x, y] of [[32, 4], [60, 32], [32, 60], [4, 32]] as const) {
    body += circle(x, y, 2.5, PALETTE.cream);
  }
  return body;
}

function drawHighlight(r: Random): string {
  const rays = r.int(2, 4);
  let body = ring(32, 32, 20, PALETTE.teal, 2, '5 4');
  body += ring(32, 32, 13, PALETTE.aqua, 1.5);
  for (let i = 0; i < rays; i += 1) {
    body += line(26 + i * 4, 4, 26 + i * 4, 12, PALETTE.amber, 2);
  }
  body += polygon([[28, 46], [36, 46], [32, 53]], PALETTE.amber);
  return body;
}

const IMPACT_RAYS: readonly Point[] = [
  [0, -20], [10, -17], [18, -9], [20, 0], [18, 9], [10, 17],
  [0, 20], [-10, 17], [-18, 9], [-20, 0], [-18, -9], [-10, -17],
];

function drawImpact(r: Random): string {
  const rays = r.int(6, 9);
  let body = '';
  for (let i = 0; i < rays && i < IMPACT_RAYS.length; i += 1) {
    const [dx, dy] = IMPACT_RAYS[i] ?? [0, 0];
    body += line(32 + dx * 0.6, 32 + dy * 0.6, 32 + dx, 32 + dy, i % 2 === 0 ? PALETTE.amber : PALETTE.rust, 3);
  }
  body += circle(32, 32, 13, PALETTE.amber);
  body += circle(32, 32, 8, PALETTE.cream);
  body += circle(32, 32, 4, PALETTE.ink);
  const sparks = r.int(2, 4);
  for (let i = 0; i < sparks; i += 1) {
    body += circle(18 + i * 12, 22 + (i % 2) * 18, 2, PALETTE.aqua);
  }
  return body;
}

function drawFallback(r: Random): string {
  const dots = r.int(2, 4);
  let body = outline([[32, 10], [54, 32], [32, 54], [10, 32]], PALETTE.slate, 3);
  body += ring(32, 32, 9, PALETTE.teal, 2);
  for (let i = 0; i < dots; i += 1) {
    body += circle(26 + i * 6, 32, 2, PALETTE.aqua);
  }
  return body;
}

/** The motifs, in a stable order. At least ten distinct gameplay categories. */
export const GAMEPLAY_CATEGORIES: readonly GameplayCategorySpec[] = [
  {
    key: 'terrain.grass',
    title: 'Town grass',
    description: 'A repeating grass tile with seeded tufts on an opaque ground.',
    kind: 'terrain',
    width: TILE,
    height: TILE,
    tileable: true,
    background: '#3f6b48',
    draw: drawGrass,
  },
  {
    key: 'terrain.water',
    title: 'Town water',
    description: 'A repeating water tile with fixed ripples and seeded glints.',
    kind: 'terrain',
    width: TILE,
    height: TILE,
    tileable: true,
    background: '#2c5d72',
    draw: drawWater,
  },
  {
    key: 'terrain.path',
    title: 'Town path',
    description: 'A repeating road tile with a straight band and seeded pebbles.',
    kind: 'terrain',
    width: TILE,
    height: TILE,
    tileable: true,
    background: '#5e6b4a',
    draw: drawPath,
  },
  {
    key: 'terrain.stone',
    title: 'Town stone',
    description: 'A repeating rocky tile with seeded chips on an opaque ground.',
    kind: 'terrain',
    width: TILE,
    height: TILE,
    tileable: true,
    background: '#4e555e',
    draw: drawStone,
  },
  {
    key: 'building.housing',
    title: 'Housing',
    description: 'A pitched-roof dwelling with a door, a chimney and seeded windows.',
    kind: 'building',
    width: TILE,
    height: TILE,
    tileable: false,
    draw: drawHousing,
  },
  {
    key: 'building.workshop',
    title: 'Workshop',
    description: 'A shed with a sawn timber stack and a wheel, for lumber production.',
    kind: 'building',
    width: TILE,
    height: TILE,
    tileable: false,
    draw: drawWorkshop,
  },
  {
    key: 'building.farm',
    title: 'Farm',
    description: 'A barn behind seeded furrows.',
    kind: 'building',
    width: TILE,
    height: TILE,
    tileable: false,
    draw: drawFarm,
  },
  {
    key: 'building.storage',
    title: 'Storage',
    description: 'A banded warehouse with stacked crates.',
    kind: 'building',
    width: TILE,
    height: TILE,
    tileable: false,
    draw: drawStorage,
  },
  {
    key: 'building.tower',
    title: 'Tower',
    description: 'A crenellated defensive tower with a slit and a pennant.',
    kind: 'building',
    width: TILE,
    height: TILE,
    tileable: false,
    draw: drawTower,
  },
  {
    key: 'unit.infantry',
    title: 'Infantry',
    description: 'A shield-and-sword figure with seeded shield studs.',
    kind: 'unit',
    width: TILE,
    height: TILE,
    tileable: false,
    draw: drawInfantry,
  },
  {
    key: 'unit.ranged',
    title: 'Ranged unit',
    description: 'An archer with a bow and seeded fletched arrows.',
    kind: 'unit',
    width: TILE,
    height: TILE,
    tileable: false,
    draw: drawRanged,
  },
  {
    key: 'unit.mounted',
    title: 'Mounted unit',
    description: 'A simplified rider on a mount with a seeded mane.',
    kind: 'unit',
    width: TILE,
    height: TILE,
    tileable: false,
    draw: drawMounted,
  },
  {
    key: 'unit.worker',
    title: 'Worker unit',
    description: 'A figure with a pick, a crate and seeded sparks.',
    kind: 'unit',
    width: TILE,
    height: TILE,
    tileable: false,
    draw: drawWorker,
  },
  {
    key: 'marker.selection',
    title: 'Selection marker',
    description: 'A dashed diamond with seeded dash length and four corner pips.',
    kind: 'marker',
    width: TILE,
    height: TILE,
    tileable: false,
    draw: drawSelection,
  },
  {
    key: 'marker.highlight',
    title: 'Highlight marker',
    description: 'Two rings, a drop chevron and seeded rays.',
    kind: 'marker',
    width: TILE,
    height: TILE,
    tileable: false,
    draw: drawHighlight,
  },
  {
    key: 'fx.impact',
    title: 'Combat impact',
    description: 'A seeded radial burst with a hot core and scattered sparks.',
    kind: 'fx',
    width: TILE,
    height: TILE,
    tileable: false,
    draw: drawImpact,
  },
  {
    key: GAMEPLAY_FALLBACK_KEY,
    title: 'Generic item',
    description: 'A neutral badge used when a content item supplies no recognised key.',
    kind: 'fallback',
    width: TILE,
    height: TILE,
    tileable: false,
    draw: drawFallback,
  },
];

/** The stable key list, for renderers that need to enumerate the vocabulary. */
export function gameplayKeys(): readonly GameplayCategory[] {
  return GAMEPLAY_CATEGORIES.map((spec) => spec.key);
}

/**
 * Neutral aliases. The keys are lower-cased, punctuation-stripped forms of
 * content classifications and caller-supplied labels. No art-derived name can
 * appear here: these words describe categories, not pictures.
 */
const ALIASES: Readonly<Record<string, GameplayCategory>> = {
  grass: 'terrain.grass',
  water: 'terrain.water',
  path: 'terrain.path',
  road: 'terrain.path',
  stone: 'terrain.stone',
  rock: 'terrain.stone',
  housing: 'building.housing',
  house: 'building.housing',
  residential: 'building.housing',
  woodfactory: 'building.workshop',
  workshop: 'building.workshop',
  lumber: 'building.workshop',
  sawmill: 'building.workshop',
  farm: 'building.farm',
  farming: 'building.farm',
  food: 'building.farm',
  storage: 'building.storage',
  warehouse: 'building.storage',
  store: 'building.storage',
  market: 'building.storage',
  tower: 'building.tower',
  defence: 'building.tower',
  defense: 'building.tower',
  fort: 'building.tower',
  infantry: 'unit.infantry',
  soldier: 'unit.infantry',
  melee: 'unit.infantry',
  ranged: 'unit.ranged',
  archer: 'unit.ranged',
  mounted: 'unit.mounted',
  cavalry: 'unit.mounted',
  rider: 'unit.mounted',
  worker: 'unit.worker',
  builder: 'unit.worker',
  selection: 'marker.selection',
  highlight: 'marker.highlight',
  impact: 'fx.impact',
  fallback: GAMEPLAY_FALLBACK_KEY,
  unknown: GAMEPLAY_FALLBACK_KEY,
};

/** This project's own neutral numeric mapping, not copied from any content. */
const SUBCATEGORIES: Readonly<Record<number, GameplayCategory>> = {
  11: 'building.housing',
  12: 'building.workshop',
  13: 'building.farm',
  14: 'building.storage',
  15: 'building.tower',
  31: 'unit.infantry',
  32: 'unit.ranged',
  33: 'unit.mounted',
  34: 'unit.worker',
};

const TYPE_DEFAULTS: Readonly<Record<string, GameplayCategory>> = {
  b: 'building.housing',
  u: 'unit.infantry',
};

const CATEGORY_DEFAULTS: Readonly<Record<number, GameplayCategory>> = {
  1: 'building.housing',
  2: 'unit.infantry',
};

const CANONICAL = new Set<string>(gameplayKeys());

function fromWord(word: string): GameplayCategory | undefined {
  return ALIASES[word.replace(/[^a-z0-9]/g, '')];
}

function fromKey(key: string): GameplayCategory {
  const lower = key.trim().toLowerCase();
  const dotted = lower.replace(/[\s:/\\]+/g, '.').replace(/^gameplay\./, '');
  if (CANONICAL.has(dotted)) return dotted as GameplayCategory;
  const last = dotted.split('.').pop() ?? '';
  const alias = fromWord(last) ?? fromWord(dotted);
  return alias ?? GAMEPLAY_FALLBACK_KEY;
}

/** Map neutral content properties to one canonical gameplay key. */
export function gameplayKey(props: GameplayContentProps): GameplayCategory {
  if (typeof props.key === 'string' && props.key.trim() !== '') return fromKey(props.key);

  if (typeof props.groupType === 'string' && props.groupType.trim() !== '') {
    const alias = fromWord(props.groupType.toLowerCase());
    if (alias) return alias;
  }

  const type = typeof props.type === 'string' ? props.type.toLowerCase() : '';
  const typeDefault = TYPE_DEFAULTS[type];
  if (typeDefault) {
    const sub = props.subcategoryId;
    if (typeof sub === 'number' && Number.isInteger(sub)) {
      const mapped = SUBCATEGORIES[sub] ?? null;
      if (mapped && mapped.startsWith(type === 'b' ? 'building.' : 'unit.')) return mapped;
    }
    return typeDefault;
  }

  const category = props.categoryId;
  if (typeof category === 'number' && Number.isInteger(category)) {
    return CATEGORY_DEFAULTS[category] ?? GAMEPLAY_FALLBACK_KEY;
  }

  return GAMEPLAY_FALLBACK_KEY;
}

function resolveKey(key: string | GameplayContentProps): GameplayCategory {
  return typeof key === 'string' ? gameplayKey({ key }) : gameplayKey(key);
}

function specFor(key: string | GameplayContentProps): GameplayCategorySpec {
  const canonical = resolveKey(key);
  return GAMEPLAY_CATEGORIES.find((spec) => spec.key === canonical)
    ?? GAMEPLAY_CATEGORIES[GAMEPLAY_CATEGORIES.length - 1]!;
}

/** The generated path of a motif. Kept for provenance, never used as a URL. */
export function gameplayArtPath(key: string | GameplayContentProps): string {
  const canonical = resolveKey(key);
  return canonical === GAMEPLAY_FALLBACK_KEY
    ? 'gameplay/fallback.svg'
    : `gameplay/${canonical.split('.').join('/')}.svg`;
}

/** A complete, standalone SVG document for one motif. Pure and deterministic. */
export function gameplayArtFor(key: string | GameplayContentProps): string {
  const spec = specFor(key);
  const drawing = spec.draw(makeRandom(seedFor(`gameplay:${spec.key}`)));
  const base = spec.tileable && spec.background ? rect(0, 0, spec.width, spec.height, spec.background) : '';
  const body = spec.tileable ? wrapTile(drawing, spec.width, spec.height) : drawing;
  return (
    '<?xml version="1.0" encoding="UTF-8"?>\n' +
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${spec.width} ${spec.height}" ` +
    `width="${spec.width}" height="${spec.height}" role="img" aria-labelledby="swl-title swl-desc">\n` +
    `  <title id="swl-title">${escapeXml(spec.title)}</title>\n` +
    `  <desc id="swl-desc">${escapeXml(spec.description)}</desc>\n` +
    base +
    body +
    '</svg>\n'
  );
}

/** Every gameplay motif, as in-memory artefacts for the CLI and the manifest. */
export function buildGameplayArt(): Array<{ path: string; bytes: Uint8Array }> {
  return GAMEPLAY_CATEGORIES.map((spec) => ({
    path: gameplayArtPath(spec.key),
    bytes: new TextEncoder().encode(gameplayArtFor(spec.key)),
  }));
}
