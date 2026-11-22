/**
 * Original FX: two short, seeded SVG frame sequences.
 *
 * Like the Foundry icons, every frame is assembled from fixed integer
 * coordinate tables and a small seeded stream. Nothing is sampled, traced or
 * derived from another game's art: the shield, the halo rings, the spark and
 * the trail are this project's own geometry and palette. The module is pure —
 * it imports only the platform-free primitives and reads no file — so the
 * browser entry can re-export it and the client can draw the same frames the
 * CLI writes to `assets/original/fx/`.
 */
import { makeRandom, seedFor } from './random.ts';
import {
  PALETTE,
  circle,
  line,
  polygon,
  svgDocument,
  type Point,
} from './svg.ts';

/** Frames in each sequence. The CSS in the client cycles this many frames. */
export const FX_FRAME_COUNT = 6;

/** Milliseconds each frame is held; six frames give a 1.2 second loop. */
export const FX_FRAME_MS = 200;

/** Eight fixed compass directions, as integer vectors, for the shield rays. */
const FX_RAYS: readonly Point[] = [
  [0, -1], [1, 0], [0, 1], [-1, 0],
  [1, -1], [1, 1], [-1, 1], [-1, -1],
];

/** A twelve-point spark around the origin, at a radius that stays in frame. */
const FX_SPARK: readonly Point[] = [
  [0, -9], [2, -3], [8, -5], [4, 0], [8, 5], [2, 3],
  [0, 9], [-2, 3], [-8, 5], [-4, 0], [-8, -5], [-2, -3],
];

/** A fixed, integer-only flight path for the moving spark. */
const FX_PATH: readonly Point[] = [
  [10, 52], [17, 45], [24, 38], [31, 31], [38, 24], [45, 17], [52, 12],
];

/** Halo colours, brightening through the pulse. */
const FX_GLOW: readonly string[] = [
  PALETTE.teal, PALETTE.teal, PALETTE.aqua,
  PALETTE.aqua, PALETTE.amber, PALETTE.cream,
];

/** Trail colours, hottest at the head and coolest at the tail. */
const FX_TRAIL: readonly string[] = [
  PALETTE.amber, PALETTE.amber, PALETTE.rust,
  PALETTE.rust, PALETTE.teal,
];

/** One animation sequence: metadata plus a pure frame-body function. */
export interface FxSequenceSpec {
  readonly id: string;
  readonly title: string;
  readonly description: string;
  readonly frames: number;
  readonly frameMs: number;
  /** The inner SVG elements for one frame, indexed from zero. */
  draw(index: number): string;
}

/**
 * A shield with an expanding halo: each frame grows the rings by three
 * pixels and brightens them, then the loop starts again. All coordinates are
 * integers, so the six frames are distinct without any clock or real maths.
 */
function drawShieldPulse(index: number): string {
  const radius = 9 + index * 3;
  const glow = FX_GLOW[index] ?? PALETTE.aqua;
  let body = '';

  // The halo goes down first so the shield always covers its centre.
  for (const [dx, dy] of FX_RAYS) {
    const inner = radius + 2;
    const outer = radius + 5 + (index % 3);
    body += line(
      32 + dx * inner, 32 + dy * inner,
      32 + dx * outer, 32 + dy * outer,
      glow, 2,
    );
  }
  body += circle(32, 32, radius, glow);
  body += circle(32, 32, Math.max(3, radius - 5), PALETTE.ink);
  body += circle(32, 32, Math.max(2, radius - 9), glow);

  // A banded heater shield, drawn from the same fixed table each frame.
  body += polygon([[32, 8], [52, 15], [50, 37], [32, 54], [14, 37], [12, 15]], PALETTE.slate);
  body += polygon([[32, 13], [47, 18], [45, 35], [32, 47], [19, 35], [17, 18]], PALETTE.teal);
  body += polygon([[19, 25], [32, 34], [45, 25], [45, 30], [32, 39], [19, 30]], PALETTE.amber);
  body += circle(32, 32, 3 + (index % 2), PALETTE.cream);
  return body;
}

/**
 * A spark travelling along the fixed path with a five-dot trail. Each frame
 * has its own seeded stream for the small jitter, so a frame is reproducible
 * on its own and the sequence never depends on the order it is generated in.
 */
function drawSparkTrail(index: number): string {
  const random = makeRandom(seedFor(`fx:spark-trail:${index}`));
  const head = FX_PATH[Math.min(index, FX_PATH.length - 1)] ?? [32, 32];
  const previous = FX_PATH[Math.max(0, index - 1)] ?? head;
  let body = line(previous[0], previous[1], head[0], head[1], PALETTE.aqua, 1);

  // Farthest dot first, so the hottest, nearest dots sit on top.
  for (let step = 5; step >= 1; step -= 1) {
    const point = FX_PATH[Math.max(0, index - step)] ?? FX_PATH[0] ?? [32, 32];
    const x = point[0] + random.int(-2, 2);
    const y = point[1] + random.int(-2, 2);
    const radius = Math.max(1, 5 - step);
    body += circle(x, y, radius, FX_TRAIL[step - 1] ?? PALETTE.amber);
  }

  const points: Point[] = FX_SPARK.map(([dx, dy]) => [head[0] + dx, head[1] + dy]);
  body += polygon(points, PALETTE.amber);
  body += circle(head[0], head[1], 5, PALETTE.cream);
  body += circle(head[0], head[1], 2, PALETTE.ink);
  return body;
}

/** The two original sequences, in a stable order. */
export const FX_SEQUENCES: readonly FxSequenceSpec[] = [
  {
    id: 'shield-pulse',
    title: 'Shield pulse',
    description: 'A banded shield under an expanding, brightening halo.',
    frames: FX_FRAME_COUNT,
    frameMs: FX_FRAME_MS,
    draw: drawShieldPulse,
  },
  {
    id: 'spark-trail',
    title: 'Spark trail',
    description: 'A bright spark travelling a fixed path with a seeded, cooling trail.',
    frames: FX_FRAME_COUNT,
    frameMs: FX_FRAME_MS,
    draw: drawSparkTrail,
  },
];

/** The generated path of one frame. Kept for provenance, never used as a URL. */
export function fxFramePath(sequenceId: string, index: number): string {
  return `fx/${sequenceId}/frame-${String(index).padStart(2, '0')}.svg`;
}

/** Find a sequence by id, or throw rather than silently drawing nothing. */
export function fxSequence(sequenceId: string): FxSequenceSpec {
  const found = FX_SEQUENCES.find((sequence) => sequence.id === sequenceId);
  if (!found) throw new Error(`unknown FX sequence: ${sequenceId}`);
  return found;
}

/** One complete, standalone SVG frame document. Pure and deterministic. */
export function fxFrameSvg(sequenceId: string, index: number): string {
  const sequence = fxSequence(sequenceId);
  if (!Number.isInteger(index) || index < 0 || index >= sequence.frames) {
    throw new Error(`FX frame out of range: ${sequenceId} ${index}`);
  }
  const title = `${sequence.title} — frame ${index + 1} of ${sequence.frames}`;
  const description =
    `${sequence.description} Original, deterministic geometry; no input art is read.`;
  return svgDocument(title, description, sequence.draw(index));
}

/** Every FX frame, as in-memory artefacts for the CLI and the manifest. */
export function buildFxFrames(): Array<{ path: string; bytes: Uint8Array }> {
  const files: Array<{ path: string; bytes: Uint8Array }> = [];
  for (const sequence of FX_SEQUENCES) {
    for (let index = 0; index < sequence.frames; index += 1) {
      files.push({
        path: fxFramePath(sequence.id, index),
        bytes: new TextEncoder().encode(fxFrameSvg(sequence.id, index)),
      });
    }
  }
  return files;
}
