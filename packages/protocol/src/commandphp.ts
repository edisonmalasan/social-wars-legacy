/**
 * The `command.php` framing.
 *
 * This is the original dialect, and the compatibility shim has to speak it
 * exactly so that the untouched `Basesec_1.5.4.swf` can play against the new
 * server with no client change.
 *
 * ## The envelope
 *
 * ```
 * <64 lowercase hex characters>;<raw JSON>
 * ```
 *
 * - The **hex** is `HMAC-SHA256(key, payload)`, in lower case.
 * - The **separator** is a single `;` (U+003B) at offset 64.
 * - The **payload** is the raw JSON string, *not* escaped.
 * - The body field is `data`, and its value is the whole `"<hex>;<json>"` string.
 *
 * ## The keys
 *
 * The key is `Config.SERVER_KEY`, and **it rotated once**: builds 1.4.5–1.4.27 use
 * `3m0d3pwiupoetn7ysa02`, and builds 1.4.28–1.5.4 use
 * `4vVSD8dftv6hdfb1Hnk9`. A shim that serves both eras has to accept both
 * keys, because unmodified clients of both eras exist.
 *
 * ## Parsing
 *
 * The client's own parser is a regular expression:
 *
 * ```as3
 * var _loc2_:RegExp = /^([0-9a-f]{64});(.*)$/i;
 * ```
 *
 * If it does not match — a plain, un-hashed JSON body — the client takes the
 * **whole input** as the payload with a null hash. That is what makes the
 * `skiphash12341` flashvar work against a hash-less server response, so the
 * parser here behaves the same way.
 */
import { createHmac, timingSafeEqual } from 'node:crypto';

/** The two server keys the client has shipped with. */
export const SERVER_KEYS = {
  /** Client builds 1.4.5 - 1.4.27. */
  legacy: '3m0d3pwiupoetn7ysa02',
  /** Client builds 1.4.28 - 1.5.4. The live-verified key. */
  current: '4vVSD8dftv6hdfb1Hnk9',
} as const;

export type ServerKey = (typeof SERVER_KEYS)[keyof typeof SERVER_KEYS];

/** Every key the shim accepts, newest first. */
export const ACCEPTED_KEYS: readonly ServerKey[] = [SERVER_KEYS.current, SERVER_KEYS.legacy];

/** The length of the hex digest prefix. */
export const SIGNATURE_LENGTH = 64;

/** The separator between the digest and the payload. */
export const SEPARATOR = ';';

/**
 * The HMAC-SHA256 digest of a payload, in lower-case hex.
 *
 * The digest is over the **raw** payload bytes — the same string that is
 * transmitted, not a re-serialisation of it.
 */
export function signPayload(payload: string, key: string): string {
  return createHmac('sha256', key).update(payload, 'utf8').digest('hex');
}

/**
 * Frame a payload: `<64 hex>;<json>`.
 */
export function framePayload(payload: string, key: string): string {
  return `${signPayload(payload, key)}${SEPARATOR}${payload}`;
}

/** A parsed frame. */
export interface ParsedFrame {
  /** The hex digest, or null when the input was not framed. */
  hash: string | null;
  /** The payload. When the input was not framed, this is the whole input. */
  payload: string;
  /** Whether the input matched the framing at all. */
  framed: boolean;
}

/**
 * Parse a frame.
 *
 * Mirrors the client's own parser exactly, including the fallback: an
 * unframed body is taken whole, with a null hash. That fallback is what
 * makes the `skiphash12341` bypass work.
 */
export function parseFrame(frame: string): ParsedFrame {
  if (frame.length >= SIGNATURE_LENGTH + 1) {
    const head = frame.slice(0, SIGNATURE_LENGTH);
    if (/^[0-9a-f]{64}$/i.test(head) && frame[SIGNATURE_LENGTH] === SEPARATOR) {
      return {
        hash: head.toLowerCase(),
        payload: frame.slice(SIGNATURE_LENGTH + 1),
        framed: true,
      };
    }
  }
  return { hash: null, payload: frame, framed: false };
}

/**
 * Verify a frame against a key.
 *
 * The comparison is constant-time, so a timing oracle cannot be used to
 * recover the digest one byte at a time.
 */
export function verifyFrame(frame: string, key: string): boolean {
  const parsed = parseFrame(frame);
  if (parsed.hash === null) return false;
  const expected = signPayload(parsed.payload, key);
  const a = Buffer.from(expected, 'hex');
  const b = Buffer.from(parsed.hash, 'hex');
  return a.length === b.length && timingSafeEqual(a, b);
}

/**
 * Verify a frame against any of the accepted keys.
 *
 * The key that matched is returned, so the shim can log which client era
 * the request came from.
 */
export function verifyFrameAny(
  frame: string,
  keys: readonly ServerKey[] = ACCEPTED_KEYS,
): ServerKey | null {
  for (const key of keys) {
    if (verifyFrame(frame, key)) return key;
  }
  return null;
}

/**
 * Frame a response.
 *
 * The client accepts **either** a raw JSON body or a framed one, and strips
 * the prefix if it is there. The upstream server answers raw JSON, and the
 * client handles it; the shim can answer either way.
 */
export function frameResponse(payload: string, key: string | null): string {
  return key === null ? payload : framePayload(payload, key);
}

/**
 * Parse a response body, whether or not it is framed.
 *
 * Mirrors the client's own response handling.
 */
export function parseResponse(body: string): ParsedFrame {
  return parseFrame(body);
}
