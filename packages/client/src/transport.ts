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
  | { ok: true; response: NativeResponse }
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

  let response: Response;
  try {
    response = await fetchImpl(`${base}/api/command`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${token}`,
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
    return { ok: true, response: (await response.json()) as NativeResponse };
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
