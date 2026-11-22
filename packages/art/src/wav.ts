/**
 * Six short original sound effects, synthesised from integers.
 *
 * The oscillators read a fixed sine table and envelopes are integer ramps,
 * so there is no runtime `Math.sin`, `Math.cos` or `Math.exp`: the bytes are
 * bit-identical on every JavaScript engine. The noise comes from the seeded
 * generator in `random.ts`, never from a captured sound.
 */
import { makeRandom, seedFor } from './random.ts';

const SAMPLE_RATE = 22050;

/** round(1000 * sin(2*pi*k/64)) for k = 0..63, compiled into the source. */
const SINE: readonly number[] = [
  0, 98, 195, 290, 383, 471, 556, 634, 707, 773, 831, 882, 924, 957, 981, 995,
  1000, 995, 981, 957, 924, 882, 831, 773, 707, 634, 556, 471, 383, 290, 195, 98,
  0, -98, -195, -290, -383, -471, -556, -634, -707, -773, -831, -882, -924, -957, -981, -995,
  -1000, -995, -981, -957, -924, -882, -831, -773, -707, -634, -556, -471, -383, -290, -195, -98,
];

type SoundKind = 'click' | 'confirm' | 'deny' | 'step' | 'impact' | 'complete';

export interface SoundSpec {
  readonly id: string;
  readonly title: string;
  readonly durationMs: number;
  readonly kind: SoundKind;
}

export const SOUND_SPECS: readonly SoundSpec[] = [
  { id: 'click', title: 'Clean-room interface click', durationMs: 70, kind: 'click' },
  { id: 'confirm', title: 'Clean-room confirmation chime', durationMs: 280, kind: 'confirm' },
  { id: 'deny', title: 'Clean-room refusal tone', durationMs: 220, kind: 'deny' },
  { id: 'step', title: 'Clean-room unit step', durationMs: 130, kind: 'step' },
  { id: 'impact', title: 'Clean-room impact', durationMs: 200, kind: 'impact' },
  { id: 'complete', title: 'Clean-room completion arpeggio', durationMs: 420, kind: 'complete' },
];

interface Phase {
  value: number;
}

/** Advance an integer phase and read the fixed sine table. */
function oscillator(phase: Phase, frequency: number): number {
  const step = Math.round(frequency * 65536 / SAMPLE_RATE);
  phase.value = (phase.value + step) & 65535;
  return SINE[(phase.value >>> 10) & 63] ?? 0;
}

/** A short linear attack, in thousandths. */
function attack(index: number, samples: number): number {
  return Math.min(1000, Math.floor(index * 1000 / Math.max(1, samples)));
}

/** A linear fall from 1000 to 0 over the whole sound. */
function fade(index: number, total: number): number {
  return 1000 - Math.floor(1000 * index / Math.max(1, total));
}

/** Square an envelope, keeping the result in thousandths. */
function squared(value: number): number {
  return Math.floor(value * value / 1000);
}

/** Combine two envelopes, keeping the result in thousandths. */
function combine(a: number, b: number): number {
  return Math.floor(a * b / 1000);
}

/** Synthesise one sound into 16-bit mono samples at the fixed sample rate. */
export function synthesise(spec: SoundSpec): Int16Array {
  const total = Math.floor(SAMPLE_RATE * spec.durationMs / 1000);
  const out = new Int16Array(total);
  const random = makeRandom(seedFor(`wav:${spec.id}`));
  const phaseA: Phase = { value: 0 };
  const phaseB: Phase = { value: 0 };
  const phaseC: Phase = { value: 0 };
  const notes = [440, 554, 659, 880];
  const segmentLength = Math.floor(total / 4);
  let lowPass = 0;

  for (let i = 0; i < total; i += 1) {
    const noise = Math.floor(random.next() * 2000) - 1000;
    let value = 0;
    switch (spec.kind) {
      case 'click': {
        const frequency = 900 - Math.floor(300 * i / total);
        const env = combine(attack(i, 2), squared(fade(i, total)));
        value = Math.floor((oscillator(phaseA, frequency) * 8 + noise * 2) / 10 * env / 1000);
        break;
      }
      case 'confirm': {
        const env = combine(attack(i, 5), fade(i, total));
        const chord = (
          oscillator(phaseA, 523) +
          oscillator(phaseB, 654) +
          oscillator(phaseC, 785)
        ) / 3;
        value = Math.floor(chord * env / 1000);
        break;
      }
      case 'deny': {
        const frequency = 420 - Math.floor(220 * i / total);
        const env = combine(attack(i, 3), squared(fade(i, total)));
        value = Math.floor((oscillator(phaseA, frequency) * 9 + noise) / 10 * env / 1000);
        break;
      }
      case 'step': {
        lowPass = Math.floor((lowPass * 82 + noise * 18) / 100);
        const env = squared(fade(i, total));
        value = Math.floor(lowPass * env / 1000 * 2);
        break;
      }
      case 'impact': {
        const frequency = 150 - Math.floor(90 * i / total);
        const env = squared(fade(i, total));
        value = Math.floor((oscillator(phaseA, frequency) * 8 + noise * 2) / 10 * env / 1000);
        break;
      }
      case 'complete': {
        const segment = Math.min(3, Math.floor(4 * i / total));
        const j = i - segment * segmentLength;
        const localFade = 1000 - Math.floor(1000 * j / Math.max(1, segmentLength));
        const env = combine(attack(j, Math.floor(segmentLength / 10)), localFade);
        const frequency = notes[segment] ?? 440;
        const fundamental = oscillator(phaseA, frequency);
        const overtone = Math.floor(oscillator(phaseB, frequency * 2) * 3 / 10);
        value = Math.floor((fundamental + overtone) * env / 1000);
        break;
      }
    }
    out[i] = Math.max(-32767, Math.min(32767, value));
  }
  return out;
}

function writeAscii(view: DataView, offset: number, text: string): void {
  for (let i = 0; i < text.length; i += 1) view.setUint8(offset + i, text.charCodeAt(i));
}

/** Encode mono 16-bit PCM samples as a canonical 44-byte-header WAV file. */
export function encodeWav(samples: Int16Array): Uint8Array {
  const dataBytes = samples.length * 2;
  const view = new DataView(new ArrayBuffer(44 + dataBytes));
  writeAscii(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataBytes, true);
  writeAscii(view, 8, 'WAVE');
  writeAscii(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, SAMPLE_RATE, true);
  view.setUint32(28, SAMPLE_RATE * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeAscii(view, 36, 'data');
  view.setUint32(40, dataBytes, true);
  for (let i = 0; i < samples.length; i += 1) view.setInt16(44 + i * 2, samples[i] ?? 0, true);
  return new Uint8Array(view.buffer);
}

/** The WAV files, as in-memory artefacts. */
export function buildSounds(): Array<{ path: string; bytes: Uint8Array }> {
  return SOUND_SPECS.map((spec) => ({
    path: `sounds/${spec.id}.wav`,
    bytes: encodeWav(synthesise(spec)),
  }));
}
