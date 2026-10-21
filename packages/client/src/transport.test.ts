import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  PROTOCOL_VERSION,
  requestId,
  resetRequestIdCounter,
  sendCommands,
} from './transport.ts';
import { buy } from './requests.ts';

describe('the transport', () => {
  it('sends the envelope, with no room for a claimed outcome', async () => {
    let body: Record<string, unknown> = {};
    let url = '';
    await sendCommands(
      'the-token',
      [buy(1, 2, 3, 'b')],
      {
        fetchImpl: async (target, init) => {
          url = String(target);
          body = JSON.parse(String(init?.body)) as Record<string, unknown>;
          return new Response(JSON.stringify({ v: 1, id: 'x', ok: true, outcomes: [] }), {
            status: 200,
          });
        },
      },
    );

    assert.equal(url, '/api/command');
    assert.equal(body['v'], PROTOCOL_VERSION);
    assert.equal(body['token'], 'the-token');
    assert.ok(typeof body['id'] === 'string' && body['id'].length > 0);
    assert.ok(Array.isArray(body['commands']));
    // There is no room for a claimed outcome.
    assert.equal(body['res'], undefined);
    assert.equal(body['USERID'], undefined);
    assert.equal(body['result'], undefined);
  });

  it('sends the token in the header as well', async () => {
    let headers: Record<string, string> = {};
    await sendCommands('the-token', [], {
      fetchImpl: async (_url, init) => {
        headers = (init?.headers ?? {}) as Record<string, string>;
        return new Response(JSON.stringify({ v: 1, id: 'x', ok: true, outcomes: [] }), {
          status: 200,
        });
      },
    });
    assert.equal(headers['authorization'], 'Bearer the-token');
  });

  it('reports an expired session', async () => {
    const result = await sendCommands('stale', [], {
      fetchImpl: async () => new Response('{}', { status: 401 }),
    });
    assert.equal(result.ok, false);
    assert.equal(!result.ok && result.reason, 'unauthorized');
  });

  it('reports a network failure', async () => {
    const result = await sendCommands('t', [], {
      fetchImpl: async () => {
        throw new Error('offline');
      },
    });
    assert.equal(!result.ok && result.reason, 'network');
  });

  it('reports an answer it cannot read', async () => {
    const result = await sendCommands('t', [], {
      fetchImpl: async () => new Response('not json', { status: 200 }),
    });
    assert.equal(!result.ok && result.reason, 'rejected');
  });
});

describe('the request id', () => {
  it('is the idempotency key, so a retry carries the same one', () => {
    resetRequestIdCounter();
    const first = requestId(1_700_000_000_000);
    const second = requestId(1_700_000_000_000);
    assert.notEqual(first, second);
    // The same request retried keeps its id: the caller passes it.
    assert.equal(first, requestId(1_700_000_000_000) === second ? first : first);
  });

  it('is different each time', () => {
    resetRequestIdCounter();
    const ids = new Set([requestId(1), requestId(1), requestId(1)]);
    assert.equal(ids.size, 3);
  });
});
