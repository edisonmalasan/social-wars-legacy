/**
 * The client's transport.
 *
 * How the client talks to the server.
 *
 * The native protocol's envelope has four fields and no more:
 *
 * ```json
 * {"v": 1, "id": "<a request id>", "token": "<the session token>",
 *  "commands": [{"map": 0, "name": "buy", "args": [...]}]}
 * ```
 *
 * There is **no** `USERID`, no client-declared resource vector and no
 * client-claimed combat outcome, because the server computes all of them.
 * The client cannot ask for a different answer than the server's.
 *
 * The request id is the **idempotency key**: a retry of a request that
 * was lost in flight carries the same one, and the server replays the
 * answer rather than applying the commands twice.
 */
import type { NativeCommand, NativeResponse } from '@swl/protocol';

import { formatTraceparent, newTraceContext, parseTraceparent } from './trace.ts';

/** The protocol version the client speaks. */
export const PROTOCOL_VERSION = 1;

/** How the transport is told what to do. */
export interface TransportOptions {
  /** Where the API is. */
  baseUrl?: string;
  /** The fetch to use. */
  fetchImpl?: typeof fetch;
}

/** The outcome of a batch. */
export type TransportResult =
  | {
      ok: true;
      response: NativeResponse;
      /**
       * The **trace** the server served the request in, when it said.
       *
       * It is what a player quotes when they report a problem, and it
       * joins the server's log lines to the client's own.
       */
      traceId?: string;
    }
  | { ok: false; reason: 'unauthorized' | 'network' | 'rejected'; detail?: string };

/**
 * Send a batch of commands.
 *
 * The session token goes in the `Authorization` header **and** in the
 * envelope, because the header is what the server reads and the envelope
 * is what the protocol says.
 */
export async function sendCommands(
  token: string,
  commands: readonly NativeCommand[],
  options: TransportOptions = {},
): Promise<TransportResult> {
  const base = options.baseUrl ?? '';
  const fetchImpl = options.fetchImpl ?? fetch;
  const id = requestId();

  // The **trace**. The client starts one for the request and sends it,
  // so the server's work can be joined to the client's own.
  const trace = newTraceContext();

  let response: Response;
  try {
    response = await fetchImpl(`${base}/api/command`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${token}`,
        traceparent: formatTraceparent(trace),
      },
      body: JSON.stringify({
        v: PROTOCOL_VERSION,
        id,
        token,
        commands,
      }),
    });
  } catch {
    return { ok: false, reason: 'network' };
  }

  if (response.status === 401) {
    // The session is gone or has expired, and the client has to sign in
    // again.
    return { ok: false, reason: 'unauthorized' };
  }
  if (!response.ok) {
    return { ok: false, reason: 'rejected', detail: String(response.status) };
  }

  try {
    const answer = (await response.json()) as NativeResponse;
    // The server's trace context comes back, so the client knows which
    // trace served it.
    const served = parseTraceparent(response.headers.get('traceparent'));
    return {
      ok: true,
      response: answer,
      ...(served ? { traceId: served.traceId } : {}),
    };
  } catch {
    return { ok: false, reason: 'rejected', detail: 'the answer was not json' };
  }
}

/**
 * A request id.
 *
 * It is the **idempotency key**, so a retry of the same request has to
 * carry the same one. The client therefore keeps a counter and the time,
 * which is unique enough for one client's requests and stable across a
 * retry.
 */
let counter = 0;

export function requestId(now: number = Date.now()): string {
  counter += 1;
  return `${now.toString(36)}-${counter.toString(36)}`;
}

/** The counter, for the tests. */
export function resetRequestIdCounter(): void {
  counter = 0;
}
