import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  ACCEPTED_KEYS,
  SERVER_KEYS,
  SEPARATOR,
  SIGNATURE_LENGTH,
  framePayload,
  frameResponse,
  parseFrame,
  parseResponse,
  signPayload,
  verifyFrame,
  verifyFrameAny,
} from './commandphp.ts';

const CAPTURE = path.join(process.cwd(), 're/evidence/live/requests.jsonl');

/** Every framed `data=` body in the live capture, URL-decoded. */
async function capturedFrames(): Promise<string[]> {
  let content: string;
  try {
    content = await readFile(CAPTURE, 'utf8');
  } catch {
    return [];
  }
  const frames: string[] = [];
  for (const line of content.split('\n')) {
    if (line.trim() === '') continue;
    let record: { body?: string };
    try {
      record = JSON.parse(line) as { body?: string };
    } catch {
      continue;
    }
    const body = record.body ?? '';
    const at = body.indexOf('data=');
    if (at < 0) continue;
    const raw = body.slice(at + 5).split('&')[0] ?? '';
    let decoded: string;
    try {
      decoded = decodeURIComponent(raw);
    } catch {
      continue;
    }
    if (parseFrame(decoded).framed) frames.push(decoded);
  }
  return frames;
}

describe('the command.php framing', () => {
  it('reproduces the digest of a REAL captured request', async () => {
    const frames = await capturedFrames();
    assert.ok(frames.length > 0, 'the live capture has no framed request');

    const frame = frames[0]!;
    const parsed = parseFrame(frame);
    assert.equal(parsed.framed, true);
    assert.equal(parsed.hash!.length, SIGNATURE_LENGTH);
    // The digest is over the raw payload bytes, and it reproduces the one the
    // original Flash client produced.
    assert.equal(signPayload(parsed.payload, SERVER_KEYS.current), parsed.hash);
    assert.equal(verifyFrame(frame, SERVER_KEYS.current), true);
  });

  it('does not verify a real captured request against the wrong key', async () => {
    const frames = await capturedFrames();
    const frame = frames[0]!;
    // The capture is from a 1.5.4 client, so it is the current key.
    assert.equal(verifyFrame(frame, SERVER_KEYS.legacy), false);
  });

  it('accepts either key, so both client eras are served', async () => {
    const frames = await capturedFrames();
    assert.equal(verifyFrameAny(frames[0]!), SERVER_KEYS.current);
  });

  it('verifies EVERY framed request in the live capture', async () => {
    const frames = await capturedFrames();
    assert.ok(frames.length > 0, 'the live capture has no framed request');
    for (const frame of frames) {
      assert.ok(
        verifyFrameAny(frame) !== null,
        `a captured request did not verify against any known key: ${frame.slice(0, 80)}`,
      );
    }
  });

  it('frames a payload the client can read back', () => {
    const payload = '{"ts":1,"commands":[]}';
    const frame = framePayload(payload, SERVER_KEYS.current);
    assert.equal(frame.length, SIGNATURE_LENGTH + 1 + payload.length);
    assert.equal(frame[SIGNATURE_LENGTH], SEPARATOR);
    const parsed = parseFrame(frame);
    assert.equal(parsed.payload, payload);
    assert.equal(verifyFrame(frame, SERVER_KEYS.current), true);
  });
});

describe('parsing an unframed body', () => {
  it('takes the whole input as the payload, with a null hash', () => {
    // This is the client's own fallback, and it is what makes the
    // `skiphash12341` flashvar work against a hash-less response.
    const body = '{"ts":1,"commands":[]}';
    const parsed = parseFrame(body);
    assert.equal(parsed.framed, false);
    assert.equal(parsed.hash, null);
    assert.equal(parsed.payload, body);
  });

  it('does not treat a body that merely looks framed as framed', () => {
    const tooShort = `abc;${'x'.repeat(80)}`;
    assert.equal(parseFrame(tooShort).framed, false);
  });

  it('does not treat non-hex as a digest', () => {
    const fake = `${'z'.repeat(64)};payload`;
    assert.equal(parseFrame(fake).framed, false);
    assert.equal(parseFrame(fake).payload, fake);
  });

  it('never verifies an unframed body', () => {
    assert.equal(verifyFrame('{"ts":1}', SERVER_KEYS.current), false);
  });
});

describe('responses', () => {
  it('can answer with a raw JSON body', () => {
    const body = '{"ok":true}';
    assert.equal(frameResponse(body, null), body);
    const parsed = parseResponse(body);
    assert.equal(parsed.framed, false);
    assert.equal(parsed.payload, body);
  });

  it('can answer with a framed body', () => {
    const body = '{"ok":true}';
    const framed = frameResponse(body, SERVER_KEYS.current);
    assert.equal(parseResponse(framed).payload, body);
    assert.equal(verifyFrame(framed, SERVER_KEYS.current), true);
  });
});

describe('the accepted keys', () => {
  it('has both eras, newest first', () => {
    assert.deepEqual(ACCEPTED_KEYS, [SERVER_KEYS.current, SERVER_KEYS.legacy]);
  });
});
