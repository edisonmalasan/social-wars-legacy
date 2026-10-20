/**
 * The server's observability.
 *
 * Two things: a **structured log** and a **metrics registry**.
 *
 * ## The log
 *
 * One line per request, as JSON, with a **request id** that ties the
 * client's action to the server's command. The id is returned in the
 * response's `x-request-id` header, so a player can quote it and the
 * exact request can be found.
 *
 * The lines are JSON rather than prose because prose cannot be queried:
 * a log you cannot filter by a player id or a command name is a log you
 * only ever read with your eyes.
 *
 * ## The metrics
 *
 * Counters, gauges and histograms, with the labels a dashboard needs:
 *
 * - **latency** — how long a request took;
 * - **command throughput** — how many commands were applied, and which;
 * - **error rate** — how many requests failed, and with what;
 * - **simulation tick time** — how long the rules engine took;
 * - **active sessions** — how many there are right now.
 *
 * There is no Prometheus client and no OpenTelemetry: the server's
 * dependencies are the ones the project chose, and a metrics endpoint
 * that returns JSON is enough for a dashboard to read and for a test to
 * assert on. Swapping the exporter later is a change in one place.
 */

/** A structured log record. */
export interface LogRecord {
  /** When it happened, as an ISO timestamp. */
  time: string;
  /** How bad it is. */
  level: 'info' | 'warn' | 'error';
  /** What happened. */
  message: string;
  /** The request it belongs to. */
  requestId?: string;
  /** Anything else the caller wants to record. */
  [field: string]: unknown;
}

/** Where the log goes. */
export type LogSink = (record: LogRecord) => void;

/** The logger. */
export interface Logger {
  /** A line at the given level. */
  log(level: LogRecord['level'], message: string, fields?: Record<string, unknown>): void;
  /** An informational line. */
  info(message: string, fields?: Record<string, unknown>): void;
  /** A warning. */
  warn(message: string, fields?: Record<string, unknown>): void;
  /** An error. */
  error(message: string, fields?: Record<string, unknown>): void;
}

/**
 * A logger that writes JSON lines.
 *
 * The sink is injected, so a test can collect the lines instead of
 * writing them, and the server can send them wherever it likes.
 */
export class JsonLogger implements Logger {
  private readonly sink: LogSink;
  private readonly clock: () => number;
  private readonly base: Record<string, unknown>;

  constructor(options: {
    sink: LogSink;
    clock?: () => number;
    base?: Record<string, unknown>;
  }) {
    this.sink = options.sink;
    this.clock = options.clock ?? (() => Date.now());
    this.base = options.base ?? {};
  }

  log(
    level: LogRecord['level'],
    message: string,
    fields: Record<string, unknown> = {},
  ): void {
    this.sink({
      ...this.base,
      ...fields,
      time: new Date(this.clock()).toISOString(),
      level,
      message,
    });
  }

  info(message: string, fields?: Record<string, unknown>): void {
    this.log('info', message, fields);
  }

  warn(message: string, fields?: Record<string, unknown>): void {
    this.log('warn', message, fields);
  }

  error(message: string, fields?: Record<string, unknown>): void {
    this.log('error', message, fields);
  }
}

/** A logger that writes nothing. */
export const SILENT_LOGGER: Logger = {
  log() {},
  info() {},
  warn() {},
  error() {},
};

/** The label key a series is recorded under. */
export function seriesKey(name: string, labels?: Record<string, string>): string {
  if (!labels) return name;
  const entries = Object.entries(labels)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .sort(([a], [b]) => a.localeCompare(b));
  if (entries.length === 0) return name;
  const rendered = entries.map(([key, value]) => `${key}=${value}`).join(',');
  return `${name}{${rendered}}`;
}

/** One histogram. */
export interface Histogram {
  /** How many observations. */
  count: number;
  /** Their sum. */
  sum: number;
  /** The smallest. */
  min: number;
  /** The largest. */
  max: number;
  /** The counts per bucket, by the bucket's upper bound. */
  buckets: Record<string, number>;
}

/** The buckets a latency histogram uses, in milliseconds. */
export const LATENCY_BUCKETS = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000];

/** The registry. */
export class Metrics {
  private readonly counterSeries = new Map<string, number>();
  private readonly gaugeSeries = new Map<string, number>();
  private readonly histogramSeries = new Map<string, Histogram>();
  private readonly buckets: readonly number[];

  constructor(options: { buckets?: readonly number[] } = {}) {
    this.buckets = options.buckets ?? LATENCY_BUCKETS;
  }

  /** Count one. */
  increment(name: string, labels?: Record<string, string>, by = 1): void {
    const key = seriesKey(name, labels);
    this.counterSeries.set(key, (this.counterSeries.get(key) ?? 0) + by);
  }

  /** Set a value that goes up and down. */
  gauge(name: string, value: number, labels?: Record<string, string>): void {
    this.gaugeSeries.set(seriesKey(name, labels), value);
  }

  /** Record one observation. */
  observe(name: string, value: number, labels?: Record<string, string>): void {
    const key = seriesKey(name, labels);
    let histogram = this.histogramSeries.get(key);
    if (!histogram) {
      histogram = {
        count: 0,
        sum: 0,
        min: Number.POSITIVE_INFINITY,
        max: Number.NEGATIVE_INFINITY,
        buckets: {},
      };
      for (const bound of this.buckets) histogram.buckets[String(bound)] = 0;
      this.histogramSeries.set(key, histogram);
    }
    histogram.count += 1;
    histogram.sum += value;
    histogram.min = Math.min(histogram.min, value);
    histogram.max = Math.max(histogram.max, value);
    for (const bound of this.buckets) {
      if (value <= bound) histogram.buckets[String(bound)]! += 1;
    }
  }

  /** The counters. */
  get counters(): Record<string, number> {
    return Object.fromEntries(this.counterSeries);
  }

  /** The gauges. */
  get gauges(): Record<string, number> {
    return Object.fromEntries(this.gaugeSeries);
  }

  /** The histograms. */
  get histograms(): Record<string, Histogram> {
    return Object.fromEntries(this.histogramSeries);
  }
}

/** A metrics snapshot, as the endpoint returns it. */
export interface MetricsSnapshot {
  /** The counters. */
  counters: Record<string, number>;
  /** The gauges. */
  gauges: Record<string, number>;
  /** The histograms. */
  histograms: Record<string, Histogram>;
}

/** The registry's snapshot. */
export function snapshot(metrics: Metrics): MetricsSnapshot {
  return {
    counters: metrics.counters,
    gauges: metrics.gauges,
    histograms: metrics.histograms,
  };
}

/**
 * A request id.
 *
 * It is a short random hex string, and the server **reuses** the one the
 * client sent when there is one, so a client's own correlation id
 * survives into the log.
 */
export function newRequestId(random: () => string = defaultRandom): string {
  return random();
}

/** The default source of randomness for a request id. */
function defaultRandom(): string {
  // The crypto module is the server's, and the rules package is not
  // allowed to depend on the platform.
  return globalThis.crypto.randomUUID().replace(/-/g, '').slice(0, 16);
}

/** The header the request id travels in. */
export const REQUEST_ID_HEADER = 'x-request-id';
