/**
 * The Foundry family: sixteen original 64x64 motifs drawn from the SVG
 * primitives. The name, the geometry, the palette and the small seeded
 * variations are all this project's own; nothing is sampled, traced or
 * derived from the original game's art.
 *
 * Each motif is a pure function of its own seeded stream, so a motif is
 * reproducible without generating any of the others first.
 */
import { makeRandom, seedFor, type Random } from './random.ts';
import {
  PALETTE,
  circle,
  ellipse,
  group,
  line,
  path,
  polygon,
  rect,
  svgDocument,
  type Point,
} from './svg.ts';

export interface Motif {
  readonly id: string;
  readonly title: string;
  readonly description: string;
  readonly kind: 'ui' | 'unit';
  draw(random: Random): string;
}

/** A fixed twelve-tooth outline: integer coordinates, no trigonometry. */
const GEAR: readonly Point[] = [
  [32, 4], [38, 10], [45, 7], [47, 15], [55, 16], [53, 24],
  [60, 29], [56, 35], [59, 43], [51, 45], [49, 53], [41, 50],
  [35, 58], [29, 52], [21, 55], [19, 47], [11, 45], [14, 37],
  [7, 32], [13, 26], [10, 18], [18, 17], [20, 9], [27, 13],
];

/** Eight rays at fixed compass points, used by the spark motif. */
const SPARK: readonly Point[] = [
  [32, 4], [38, 23], [57, 17], [43, 32], [57, 47], [38, 41],
  [32, 60], [26, 41], [7, 47], [21, 32], [7, 17], [26, 23],
];

export const MOTIFS: readonly Motif[] = [
  {
    id: 'foundry-anvil',
    title: 'Foundry anvil',
    description: 'A workshop anvil on a short plinth, with a struck horn.',
    kind: 'unit',
    draw(r) {
      const marks = r.int(2, 4);
      let body = polygon([[12, 39], [52, 39], [48, 51], [16, 51]], PALETTE.slate);
      body += rect(9, 29, 46, 10, PALETTE.amber, 2);
      body += polygon([[55, 31], [63, 34], [55, 37]], PALETTE.amber);
      body += rect(17, 51, 30, 6, PALETTE.ink, 1);
      body += circle(16, 34, 1.5, PALETTE.cream) + circle(48, 34, 1.5, PALETTE.cream);
      for (let i = 0; i < marks; i += 1) body += circle(22 + i * 7, 45, 1, PALETTE.aqua);
      return body;
    },
  },
  {
    id: 'foundry-banner',
    title: 'Foundry banner',
    description: 'A notched pennant on a studded pole.',
    kind: 'ui',
    draw(r) {
      const studs = r.int(2, 4);
      let body = line(20, 8, 20, 56, PALETTE.ink, 4);
      body += polygon([[22, 12], [54, 12], [48, 22], [54, 32], [22, 32]], PALETTE.amber);
      body += polygon([[25, 16], [48, 16], [44, 22], [48, 28], [25, 28]], PALETTE.rust);
      body += circle(20, 8, 3, PALETTE.cream);
      for (let i = 0; i < studs; i += 1) body += circle(20, 26 + i * 9, 1, PALETTE.aqua);
      return body;
    },
  },
  {
    id: 'foundry-cog',
    title: 'Foundry cog',
    description: 'A toothed wheel with a hub and a measured number of spokes.',
    kind: 'ui',
    draw(r) {
      const spokes = r.int(4, 6);
      let body = polygon(GEAR, PALETTE.slate);
      body += circle(32, 32, 13, PALETTE.amber);
      for (let i = 0; i < spokes; i += 1) {
        const x = 32 + (i % 2 === 0 ? 9 : -9);
        const y = 32 + (i < spokes / 2 ? 9 : -9);
        body += line(32, 32, x, y, PALETTE.rust, 2);
      }
      body += circle(32, 32, 6, PALETTE.ink);
      return body;
    },
  },
  {
    id: 'foundry-hammer',
    title: 'Foundry hammer',
    description: 'A cross-peen hammer, angled for the forge.',
    kind: 'unit',
    draw(r) {
      const rivets = r.int(1, 3);
      let tool = rect(29, 22, 6, 36, PALETTE.rust, 2);
      tool += rect(16, 14, 32, 12, PALETTE.slate, 2);
      tool += rect(46, 14, 6, 12, PALETTE.amber, 1);
      for (let i = 0; i < rivets; i += 1) tool += circle(22 + i * 8, 20, 1, PALETTE.cream);
      return group(tool, 'rotate(35 32 32)');
    },
  },
  {
    id: 'foundry-shield',
    title: 'Foundry shield',
    description: 'A banded heater shield with a chevron and vertical ribs.',
    kind: 'unit',
    draw(r) {
      const ribs = r.int(2, 4);
      let body = polygon([[32, 6], [54, 14], [52, 38], [32, 56], [12, 38], [10, 14]], PALETTE.slate);
      body += polygon([[32, 12], [48, 18], [46, 36], [32, 49], [18, 36], [16, 18]], PALETTE.teal);
      body += polygon([[18, 24], [32, 34], [46, 24], [46, 29], [32, 39], [18, 29]], PALETTE.amber);
      for (let i = 0; i < ribs; i += 1) {
        const x = 24 + i * 8;
        body += line(x, 16, x, 30, PALETTE.aqua, 1);
      }
      return body;
    },
  },
  {
    id: 'foundry-lantern',
    title: 'Foundry lantern',
    description: 'A hanging lantern with a luminous glass and a measured halo.',
    kind: 'ui',
    draw(r) {
      const rays = r.int(4, 7);
      let body = path('M24 14 Q32 5 40 14', 'none', PALETTE.ink, 3);
      body += rect(22, 13, 20, 5, PALETTE.slate, 1);
      body += circle(32, 33, 10, PALETTE.amber);
      body += circle(32, 33, 5, PALETTE.cream);
      body += rect(22, 41, 20, 5, PALETTE.slate, 1);
      for (let i = 0; i < rays; i += 1) {
        const y = 18 + i * 5;
        body += line(46, y, 54 + (i % 2) * 3, y - 2, PALETTE.amber, 2);
      }
      return body;
    },
  },
  {
    id: 'foundry-cauldron',
    title: 'Foundry cauldron',
    description: 'A round pot on two feet, with a variable number of bubbles.',
    kind: 'ui',
    draw(r) {
      const bubbles = r.int(2, 5);
      let body = path('M13 28 Q12 51 32 51 Q52 51 51 28 Z', PALETTE.slate);
      body += ellipse(32, 28, 19, 7, PALETTE.ink);
      body += ellipse(32, 28, 15, 4, PALETTE.teal);
      body += rect(17, 50, 6, 6, PALETTE.ink, 1) + rect(41, 50, 6, 6, PALETTE.ink, 1);
      for (let i = 0; i < bubbles; i += 1) {
        body += circle(23 + i * 5, 20 - (i % 2) * 5, 2 + (i % 2), PALETTE.aqua);
      }
      return body;
    },
  },
  {
    id: 'foundry-compass',
    title: 'Foundry compass',
    description: 'A cased compass with fixed ticks and a two-part needle.',
    kind: 'ui',
    draw(r) {
      const heavy = r.int(0, 1) === 1;
      let body = circle(32, 32, 24, PALETTE.slate);
      body += circle(32, 32, 19, PALETTE.cream);
      const ticks: readonly Point[] = [[32, 13], [45, 19], [51, 32], [45, 45], [32, 51], [19, 45], [13, 32], [19, 19]];
      for (let i = 0; i < ticks.length; i += 1) {
        const [x, y] = ticks[i] ?? [32, 32];
        body += line(32, 32, x, y, i % 2 === 0 ? PALETTE.ink : PALETTE.aqua, 1);
      }
      body += polygon([[32, 15], [38, 34], [32, 30]], PALETTE.rust);
      body += polygon([[32, 49], [26, 30], [32, 34]], heavy ? PALETTE.ink : PALETTE.teal);
      body += circle(32, 32, 3, PALETTE.amber);
      return body;
    },
  },
  {
    id: 'foundry-pick',
    title: 'Foundry pick',
    description: 'A double-pointed pick with a curved head.',
    kind: 'unit',
    draw(r) {
      const grip = r.int(2, 4);
      let body = line(17, 53, 45, 19, PALETTE.rust, 5);
      body += path('M18 18 Q32 9 50 18', 'none', PALETTE.slate, 7);
      body += polygon([[10, 12], [21, 16], [16, 24]], PALETTE.amber);
      body += polygon([[54, 12], [43, 16], [48, 24]], PALETTE.amber);
      for (let i = 0; i < grip; i += 1) body += line(20 + i * 2, 48 - i * 3, 24 + i * 2, 52 - i * 3, PALETTE.ink, 1);
      return body;
    },
  },
  {
    id: 'foundry-quiver',
    title: 'Foundry quiver',
    description: 'A leather quiver holding a variable number of fletched shafts.',
    kind: 'unit',
    draw(r) {
      const arrows = r.int(2, 4);
      let body = polygon([[22, 22], [40, 22], [38, 54], [24, 54]], PALETTE.rust);
      body += ellipse(31, 22, 9, 4, PALETTE.amber);
      for (let i = 0; i < arrows; i += 1) {
        const x = 26 + i * 4;
        body += line(x, 21, x, 8, PALETTE.slate, 2);
        body += polygon([[x - 2, 10], [x + 2, 8], [x + 2, 14]], PALETTE.aqua);
      }
      body += line(24, 38, 38, 38, PALETTE.ink, 2);
      return body;
    },
  },
  {
    id: 'foundry-spark',
    title: 'Foundry spark',
    description: 'A twelve-point spark with a bright core.',
    kind: 'ui',
    draw(r) {
      const inset = r.int(0, 2);
      const scaled: Point[] = SPARK.map(([x, y]) => [32 + (x - 32) * (100 - inset * 6) / 100, 32 + (y - 32) * (100 - inset * 6) / 100]);
      return polygon(scaled, PALETTE.amber) + circle(32, 32, 7, PALETTE.cream) + circle(32, 32, 3, PALETTE.ink);
    },
  },
  {
    id: 'foundry-turret',
    title: 'Foundry turret',
    description: 'A squat turret on a plinth, with crenellations and a barrel.',
    kind: 'unit',
    draw(r) {
      const merlons = r.int(2, 4);
      let body = rect(12, 44, 40, 12, PALETTE.slate, 2);
      body += rect(18, 24, 28, 20, PALETTE.teal, 2);
      body += rect(30, 12, 10, 16, PALETTE.slate, 1);
      body += rect(29, 9, 12, 5, PALETTE.amber, 1);
      for (let i = 0; i < merlons; i += 1) body += rect(19 + i * 8, 19, 5, 6, PALETTE.cream, 1);
      return body;
    },
  },
  {
    id: 'foundry-wagon',
    title: 'Foundry wagon',
    description: 'A covered wagon with spoked wheels.',
    kind: 'unit',
    draw(r) {
      const spokes = r.int(3, 5);
      let body = rect(10, 32, 40, 12, PALETTE.rust, 2);
      body += path('M12 32 Q32 12 48 32 Z', PALETTE.amber);
      for (const cx of [18, 44]) {
        body += circle(cx, 48, 7, PALETTE.slate);
        body += circle(cx, 48, 2, PALETTE.ink);
        for (let i = 0; i < spokes; i += 1) {
          const y = 44 + i * 2;
          body += line(cx - 5, y, cx + 5, y, PALETTE.cream, 1);
        }
      }
      return body;
    },
  },
  {
    id: 'foundry-flask',
    title: 'Foundry flask',
    description: 'A stoppered flask with liquid and a variable number of bubbles.',
    kind: 'ui',
    draw(r) {
      const bubbles = r.int(2, 4);
      let body = rect(29, 8, 6, 18, PALETTE.cream, 1);
      body += rect(28, 4, 8, 6, PALETTE.rust, 1);
      body += path('M29 24 Q13 34 18 48 Q32 59 46 48 Q51 34 35 24 Z', 'none', PALETTE.slate, 3);
      body += path('M21 42 Q32 47 43 42 Q46 48 32 53 Q18 48 21 42 Z', PALETTE.teal);
      for (let i = 0; i < bubbles; i += 1) body += circle(27 + i * 4, 36 - (i % 2) * 6, 2, PALETTE.aqua);
      return body;
    },
  },
  {
    id: 'foundry-wrench',
    title: 'Foundry wrench',
    description: 'An open-ended spanner with a ring handle.',
    kind: 'ui',
    draw(r) {
      const teeth = r.int(1, 2);
      let body = line(18, 46, 43, 21, PALETTE.slate, 7);
      body += polygon([[40, 9], [55, 9], [55, 19], [49, 19], [49, 14], [44, 14], [44, 19], [38, 19]], PALETTE.amber);
      for (let i = 0; i < teeth; i += 1) body += rect(50 - i * 4, 10, 2, 4, PALETTE.ink, 0);
      body += circle(16, 48, 7, PALETTE.slate) + circle(16, 48, 3, PALETTE.ink);
      return body;
    },
  },
  {
    id: 'foundry-boot',
    title: 'Foundry boot',
    description: 'A laced work boot on a thick sole.',
    kind: 'unit',
    draw(r) {
      const laces = r.int(2, 4);
      let body = polygon([[24, 8], [38, 8], [38, 34], [52, 38], [54, 50], [16, 50], [16, 40]], PALETTE.rust);
      body += rect(14, 49, 42, 6, PALETTE.ink, 2);
      body += rect(22, 8, 18, 6, PALETTE.slate, 2);
      for (let i = 0; i < laces; i += 1) body += line(25, 18 + i * 5, 35, 18 + i * 5, PALETTE.cream, 1);
      return body;
    },
  },
];

/** The icon files, as in-memory artefacts. */
export function buildIcons(): Array<{ path: string; bytes: Uint8Array }> {
  const files: Array<{ path: string; bytes: Uint8Array }> = [];
  for (const motif of MOTIFS) {
    const body = motif.draw(makeRandom(seedFor(motif.id)));
    const svg = svgDocument(motif.title, motif.description, body);
    files.push({ path: `icons/${motif.id}.svg`, bytes: new TextEncoder().encode(svg) });
  }
  files.push({ path: 'icons/sprite-sheet.svg', bytes: new TextEncoder().encode(spriteSheet()) });
  return files;
}

/** A 4x4 sheet of `<symbol>`/`<use>` references to the same sixteen motifs. */
export function spriteSheet(): string {
  let defs = '';
  let uses = '';
  MOTIFS.forEach((motif, index) => {
    const body = motif.draw(makeRandom(seedFor(motif.id)));
    defs += `    <symbol id="swl-${motif.id}" viewBox="0 0 64 64">\n${body}    </symbol>\n`;
    const x = 8 + (index % 4) * 80;
    const y = 8 + Math.floor(index / 4) * 80;
    uses += `    <use href="#swl-${motif.id}" x="${x}" y="${y}" width="64" height="64"/>\n`;
  });
  return (
    '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 320" width="320" height="320" ' +
    'role="img" aria-labelledby="swl-title swl-desc">\n' +
    '  <title id="swl-title">Foundry sprite sheet</title>\n' +
    '  <desc id="swl-desc">The sixteen original Foundry motifs, laid out in a four by four grid.</desc>\n' +
    '  <defs>\n' + defs + '  </defs>\n' + uses +
    '</svg>\n'
  );
}
