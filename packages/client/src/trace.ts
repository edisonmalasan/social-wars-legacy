/**
 * The client's trace.
 *
 * The client starts a **trace** for a request and sends it in the
 * standard `traceparent` header, so the server's work on the request
 * can be joined to the client's own. The server's answer carries the
 * trace context back, so a player can quote the span that served them.
 *
 * The random numbers come from the **platform's** own source — the
 * browser's `crypto.getRandomValues` and Node's `crypto` — because the
 * client package runs in both, and it must not depend on either.
 */

/** 32 hex characters: a trace id. */
export function newTraceId(): string {
  return randomHex(16);
}

/** 16 hex characters: a span id. */
export function newSpanId(): string {
  return randomHex(8);
}

/** The random bytes, in hex. */
function randomHex(bytes: number): string {
  const buffer = new Uint8Array(bytes);
  globalThis.crypto.getRandomValues(buffer);
  let out = '';
  for (const byte of buffer) out += byte.toString(16).padStart(2, '0');
  return out;
}

/** A trace context. */
export interface TraceContext {
  /** The trace's id: 32 hex characters. */
  readonly traceId: string;
  /** This span's id: 16 hex characters. */
  readonly spanId: string;
  /** Whether the trace is sampled. */
  readonly sampled: boolean;
}

/** A fresh trace context. */
export function newTraceContext(): TraceContext {
  return { traceId: newTraceId(), spanId: newSpanId(), sampled: true };
}

/** Write a `traceparent` header. */
export function formatTraceparent(context: TraceContext): string {
  const flags = context.sampled ? '01' : '00';
  return `00-${context.traceId}-${context.spanId}-${flags}`;
}

/**
 * Read a `traceparent` header.
 *
 * A header that is not the shape the standard says is **ignored**:
 * a trace is an aid and not a requirement.
 */
export function parseTraceparent(header: string | null | undefined): TraceContext | null {
  if (!header) return null;
  const parts = header.trim().split('-');
  if (parts.length !== 4) return null;
  const [version, traceId, spanId, flags] = parts as [string, string, string, string];
  if (!/^[0-9a-f]{2}$/.test(version)) return null;
  if (!/^[0-9a-f]{32}$/.test(traceId)) return null;
  if (!/^[0-9a-f]{16}$/.test(spanId)) return null;
  if (!/^[0-9a-f]{2}$/.test(flags)) return null;
  return {
    traceId,
    spanId,
    sampled: (parseInt(flags, 16) & 0x01) === 0x01,
  };
}
