/**
 * Distributed tracing.
 *
 * A **request id** says which log lines belong together. It does not
 * say how the request got there, and it does not cross a process
 * boundary: the client's id is the server's id, and nothing says that
 * the database was slow rather than the rules engine.
 *
 * A **trace** does. It is a tree of spans, one per unit of work, and
 * it is carried across processes in the standard `traceparent` header:
 *
 * ```
 * traceparent: 00-<32 hex trace id>-<16 hex span id>-<2 hex flags>
 * ```
 *
 * The client starts a trace, the server continues it as a child span,
 * and the database's queries are spans under that. The whole thing
 * ends up in the log lines and in the metrics, so a slow request can
 * be **attributed** rather than merely observed.
 *
 * ## The format is the W3C's
 *
 * The header's shape is the W3C Trace Context's, so an ordinary
 * tracing library can read what this writes and this can read what
 * ordinary libraries write. A malformed or absent header is not an
 * error: a new trace is started, because a trace is an aid and not a
 * requirement.
 */
import { AsyncLocalStorage } from 'node:async_hooks';
import { randomBytes } from 'node:crypto';

import type { Database } from './pgstore.ts';

/** The header the trace context travels in. */
export const TRACEPARENT_HEADER = 'traceparent';

/** The version this implementation speaks. */
export const TRACEPARENT_VERSION = '00';

/** A trace context: the trace, the span, and the span's parent. */
export interface TraceContext {
  /** The trace's id: 32 hex characters, and the same for every span. */
  readonly traceId: string;
  /** This span's id: 16 hex characters. */
  readonly spanId: string;
  /** The span this one hangs from, when there is one. */
  readonly parentSpanId: string | null;
  /** Whether the trace is sampled. */
  readonly sampled: boolean;
}

/** A span: one unit of work inside a trace. */
export interface Span {
  /** What the work was. */
  readonly name: string;
  /** The span's own context. */
  readonly context: TraceContext;
  /** When it started, in milliseconds. */
  readonly startedAt: number;
  /** When it ended, in milliseconds. Null while it is still running. */
  endedAt: number | null;
  /** What was learned while it ran. */
  attributes: Record<string, unknown>;
}

/** 32 hex characters: a trace id. */
export function newTraceId(): string {
  return randomBytes(16).toString('hex');
}

/** 16 hex characters: a span id. */
export function newSpanId(): string {
  return randomBytes(8).toString('hex');
}

/**
 * Read a `traceparent` header.
 *
 * A header that is not the shape the standard says is **ignored**,
 * rather than being an error: a client that sends nonsense must not
 * be able to break the request.
 */
export function parseTraceparent(header: string | undefined): TraceContext | null {
  if (!header) return null;
  const parts = header.trim().split('-');
  if (parts.length !== 4) return null;
  const [version, traceId, spanId, flags] = parts as [string, string, string, string];

  // The version must be two hex characters, and the ids must be the
  // right length. All zeroes are not a valid id.
  if (!/^[0-9a-f]{2}$/.test(version)) return null;
  if (!/^[0-9a-f]{32}$/.test(traceId)) return null;
  if (!/^[0-9a-f]{16}$/.test(spanId)) return null;
  if (!/^[0-9a-f]{2}$/.test(flags)) return null;
  if (/^0+$/.test(traceId) || /^0+$/.test(spanId)) return null;

  return {
    traceId,
    spanId,
    parentSpanId: null,
    sampled: (parseInt(flags, 16) & 0x01) === 0x01,
  };
}

/** Write a `traceparent` header. */
export function formatTraceparent(context: TraceContext): string {
  const flags = context.sampled ? '01' : '00';
  return `${TRACEPARENT_VERSION}-${context.traceId}-${context.spanId}-${flags}`;
}

/**
 * Start a span.
 *
 * A span under a parent continues the parent's trace and hangs from
 * the parent's span. A span with no parent starts a trace of its own.
 */
export function startSpan(
  parent: TraceContext | null,
  name: string,
  now: () => number = () => Date.now(),
): Span {
  const context: TraceContext = parent
    ? {
        traceId: parent.traceId,
        spanId: newSpanId(),
        parentSpanId: parent.spanId,
        sampled: parent.sampled,
      }
    : {
        traceId: newTraceId(),
        spanId: newSpanId(),
        parentSpanId: null,
        sampled: true,
      };

  return {
    name,
    context,
    startedAt: now(),
    endedAt: null,
    attributes: {},
  };
}

/** End a span, with what was learned while it ran. */
export function endSpan(
  span: Span,
  attributes: Record<string, unknown> = {},
  now: () => number = () => Date.now(),
): Span {
  span.endedAt = now();
  Object.assign(span.attributes, attributes);
  return span;
}

/** The span that is running now, if there is one. */
const storage = new AsyncLocalStorage<Span>();

/**
 * Run some work inside a span.
 *
 * The span is the **current** one for the duration, so anything deeper
 * — the database — can make a child of it without being passed
 * anything.
 */
export function runInSpan<T>(span: Span, work: () => T): T {
  return storage.run(span, work);
}

/** The span that is running now, if there is one. */
export function currentSpan(): Span | null {
  return storage.getStore() ?? null;
}

/**
 * A database that reports what it does.
 *
 * Every statement becomes a **child span** of whatever is running, so
 * the slow query under a slow request is visible as such. The
 * statement is reduced to its **shape** — the table and the verb — so
 * that no value from a player's save is written to the log.
 */
export function tracedDatabase(
  db: Database,
  now: () => number = () => Date.now(),
): Database {
  return {
    async exec(sql: string): Promise<unknown> {
      const parent = currentSpan();
      if (!parent) return db.exec(sql);
      const span = startSpan(parent.context, `db: ${statementShape(sql)}`, now);
      return runInSpan(span, async () => {
        try {
          const result = await db.exec(sql);
          endSpan(span, { 'db.rows': 0 }, now);
          return result;
        } catch (error) {
          endSpan(span, { 'error': String(error) }, now);
          throw error;
        }
      });
    },
    async query<Row = Record<string, unknown>>(
      sql: string,
      params?: readonly unknown[],
    ): Promise<{ rows: Row[]; affectedRows?: number }> {
      const parent = currentSpan();
      if (!parent) return db.query<Row>(sql, params);
      const span = startSpan(parent.context, `db: ${statementShape(sql)}`, now);
      return runInSpan(span, async () => {
        try {
          const result = await db.query<Row>(sql, params);
          endSpan(span, { 'db.rows': result.rows.length }, now);
          return result;
        } catch (error) {
          endSpan(span, { error: String(error) }, now);
          throw error;
        }
      });
    },
  };
}

/**
 * A statement's shape.
 *
 * The verb and the table, and nothing else: a statement's **values**
 * can carry a player's save, and a log line is not the place for that.
 */
export function statementShape(sql: string): string {
  const text = sql.trim().replace(/\s+/g, ' ');
  const verb = text.split(' ')[0] ?? '';
  const upper = verb.toUpperCase();
  if (upper === 'SELECT' || upper === 'INSERT' || upper === 'UPDATE' || upper === 'DELETE') {
    const table = /\b(?:FROM|INTO|UPDATE)\s+([A-Za-z_][A-Za-z0-9_]*)/i.exec(text);
    if (table) return `${upper} ${table[1]}`;
  }
  return upper;
}
