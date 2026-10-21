import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  endSpan,
  formatTraceparent,
  newSpanId,
  newTraceId,
  parseTraceparent,
  runInSpan,
  startSpan,
  statementShape,
  tracedDatabase,
} from './tracing.ts';
import type { Database } from './pgstore.ts';

describe('the trace context', () => {
  it('reads a well-formed header', () => {
    const context = parseTraceparent('00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01');
    assert.ok(context);
    assert.equal(context!.traceId, '4bf92f3577b34da6a3ce929d0e0e4736');
    assert.equal(context!.spanId, '00f067aa0ba902b7');
    assert.equal(context!.sampled, true);
  });

  it('ignores a malformed header, because a trace is not a requirement', () => {
    for (const header of [
      '',
      'nonsense',
      '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7',
      '00-short-00f067aa0ba902b7-01',
      '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01-extra',
      '00-00000000000000000000000000000000-00f067aa0ba902b7-01',
      '00-4bf92f3577b34da6a3ce929d0e0e4736-0000000000000000-01',
      'zz-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01',
    ]) {
      assert.equal(parseTraceparent(header), null, `the header "${header}"`);
    }
    assert.equal(parseTraceparent(undefined), null);
  });

  it('round-trips', () => {
    const context = parseTraceparent(
      formatTraceparent({
        traceId: newTraceId(),
        spanId: newSpanId(),
        parentSpanId: null,
        sampled: false,
      }),
    );
    assert.ok(context);
    assert.equal(context!.sampled, false);
  });

  it('makes ids of the right shape', () => {
    assert.match(newTraceId(), /^[0-9a-f]{32}$/);
    assert.match(newSpanId(), /^[0-9a-f]{16}$/);
  });
});

describe('the spans', () => {
  it('a child continues the trace and hangs from its parent', () => {
    const parent = parseTraceparent(
      '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01',
    );
    const child = startSpan(parent, 'http: GET');
    assert.equal(child.context.traceId, parent!.traceId);
    assert.equal(child.context.parentSpanId, parent!.spanId);
    assert.notEqual(child.context.spanId, parent!.spanId);
  });

  it('a span with no parent starts a trace of its own', () => {
    const span = startSpan(null, 'http: GET');
    assert.equal(span.context.parentSpanId, null);
    assert.match(span.context.traceId, /^[0-9a-f]{32}$/);
  });

  it('records when it ended and what it learned', () => {
    let clock = 100;
    const span = startSpan(null, 'work', () => clock);
    assert.equal(span.endedAt, null);
    clock = 250;
    endSpan(span, { 'db.rows': 3 }, () => clock);
    assert.equal(span.endedAt, 250);
    assert.equal(span.attributes['db.rows'], 3);
  });
});

describe('the traced database', () => {
  /** A database that remembers what it was asked. */
  function fake(): Database & { seen: string[] } {
    const seen: string[] = [];
    return {
      seen,
      async exec(sql: string) {
        seen.push(sql);
        return { ok: true };
      },
      async query<Row = Record<string, unknown>>(sql: string) {
        seen.push(sql);
        return { rows: [] as Row[] };
      },
    };
  }

  it('makes a child span of whatever is running', () => {
    const db = fake();
    const traced = tracedDatabase(db);
    const parent = startSpan(null, 'http: GET');
    runInSpan(parent, async () => {
      await traced.query('SELECT doc FROM player_saves WHERE player_id = $1', ['me']);
    });
    assert.equal(db.seen.length, 1);
  });

  it('works with no span running', async () => {
    const db = fake();
    const traced = tracedDatabase(db);
    await traced.query('SELECT 1');
    assert.equal(db.seen.length, 1);
  });

  it('reduces a statement to its shape, so that no value is logged', () => {
    assert.equal(statementShape('SELECT doc FROM player_saves WHERE player_id = $1'), 'SELECT player_saves');
    assert.equal(statementShape('UPDATE player_saves SET doc = $1'), 'UPDATE player_saves');
    assert.equal(statementShape('INSERT INTO social (id) VALUES ($1)'), 'INSERT social');
    assert.equal(statementShape('DELETE FROM social WHERE id = $1'), 'DELETE social');
    assert.equal(statementShape('BEGIN'), 'BEGIN');
  });
});
