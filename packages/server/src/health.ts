/**
 * The server's health.
 *
 * The server has to be able to say whether it is well, and it has to say
 * it in a form a machine can act on. Two things come out of it:
 *
 * - a **health report**: the status, the versions in use, the
 *   measurements, and the alerts that are firing;
 * - the **alert rules** themselves, so the thresholds are written down
 *   rather than being whatever the code happens to compare against.
 *
 * ## The measurements
 *
 * Five, and they are the ones an operator actually watches:
 *
 * | Measurement | What it is |
 * |---|---|
 * | `error_rate` | the failed requests over all the requests |
 * | `latency_p95_ms` | the ninety-fifth percentile of the request time |
 * | `tick_p95_ms` | the ninety-fifth percentile of the simulation time |
 * | `active_sessions` | how many sessions are live |
 * | `command_rate` | how many commands a second are being applied |
 *
 * The percentiles come from the **histograms**, which are bucketed, so
 * they are the bucket the percentile falls in and not an exact value.
 * That is enough to alert on and it is honest about what it is.
 */
import type { Metrics } from './observability.ts';

/** How a measurement is compared with its threshold. */
export type Comparison = 'above' | 'below';

/** One alert rule. */
export interface AlertRule {
  /** The rule's name. */
  name: string;
  /** The measurement it watches. */
  measurement: string;
  /** Which way the comparison goes. */
  comparison: Comparison;
  /** The threshold. */
  threshold: number;
  /** How bad it is. */
  severity: 'warning' | 'critical';
  /** What to do about it. */
  hint: string;
}

/** The alert rules the server ships with. */
export const ALERT_RULES: readonly AlertRule[] = [
  {
    name: 'error-rate',
    measurement: 'error_rate',
    comparison: 'above',
    threshold: 0.1,
    severity: 'critical',
    hint: 'A tenth of the requests are failing. Check the logs and the database.',
  },
  {
    name: 'error-rate-warning',
    measurement: 'error_rate',
    comparison: 'above',
    threshold: 0.02,
    severity: 'warning',
    hint: 'Two requests in a hundred are failing. Watch it.',
  },
  {
    name: 'latency',
    measurement: 'latency_p95_ms',
    comparison: 'above',
    threshold: 500,
    severity: 'warning',
    hint: 'The slow requests are over half a second. Something is waiting.',
  },
  {
    name: 'latency-critical',
    measurement: 'latency_p95_ms',
    comparison: 'above',
    threshold: 2_000,
    severity: 'critical',
    hint: 'The slow requests are over two seconds. The server is struggling.',
  },
  {
    name: 'tick-time',
    measurement: 'tick_p95_ms',
    comparison: 'above',
    threshold: 100,
    severity: 'warning',
    hint: 'The simulation is taking over a hundred milliseconds. It is the clock.',
  },
  {
    name: 'tick-time-critical',
    measurement: 'tick_p95_ms',
    comparison: 'above',
    threshold: 500,
    severity: 'critical',
    hint: 'The simulation is taking half a second. The server cannot keep up.',
  },
];

/** One measurement. */
export interface Measurement {
  /** Its name. */
  name: string;
  /** Its value. */
  value: number;
  /** The unit it is in. */
  unit: 'ratio' | 'ms' | 'count' | 'per_second';
}

/** An alert that is firing. */
export interface Alert {
  /** The rule's name. */
  name: string;
  /** The measurement's value. */
  value: number;
  /** The threshold it is over. */
  threshold: number;
  /** How bad it is. */
  severity: 'warning' | 'critical';
  /** What to do about it. */
  hint: string;
}

/** The server's health. */
export interface HealthReport {
  /** Whether the server is well. */
  status: 'ok' | 'degraded' | 'unhealthy';
  /** The server's version. */
  version: string;
  /** The content bundle's build id. */
  contentBuildId: string;
  /** The asset bundle's build id, when it is known. */
  assetBuildId: string | null;
  /** How long the server has been up, in seconds. */
  uptimeSeconds: number;
  /** The measurements. */
  measurements: Measurement[];
  /** The alerts that are firing. */
  alerts: Alert[];
  /** How many sessions are live. */
  activeSessions: number;
}

/**
 * The percentile of a histogram.
 *
 * The buckets are cumulative, so the percentile is the first bucket
 * whose count reaches it.
 */
export function percentile(
  histogram: { count: number; buckets: Record<string, number> } | undefined,
  fraction: number,
): number {
  if (!histogram || histogram.count === 0) return 0;
  const target = histogram.count * fraction;
  const bounds = Object.keys(histogram.buckets)
    .map(Number)
    .sort((a, b) => a - b);
  for (const bound of bounds) {
    if ((histogram.buckets[String(bound)] ?? 0) >= target) return bound;
  }
  return bounds[bounds.length - 1] ?? 0;
}

/** The measurements, read out of the metrics. */
export function measurements(
  metrics: Metrics,
  activeSessions: number,
  elapsedSeconds: number,
): Measurement[] {
  const counters = metrics.counters;
  const requests = Object.entries(counters)
    .filter(([key]) => key.startsWith('http_requests_total'))
    .reduce((sum, [, value]) => sum + value, 0);
  const errors = Object.entries(counters)
    .filter(([key]) => key.startsWith('http_errors_total'))
    .reduce((sum, [, value]) => sum + value, 0);

  const latency = percentile(
    metrics.histograms['http_request_duration_ms{method=GET,path=/health}'] ??
      firstHistogram(metrics, 'http_request_duration_ms'),
    0.95,
  );
  const tick = percentile(firstHistogram(metrics, 'simulation_tick_ms'), 0.95);
  const commands = Object.entries(counters)
    .filter(([key]) => key.startsWith('commands_total'))
    .reduce((sum, [, value]) => sum + value, 0);

  return [
    {
      name: 'error_rate',
      value: requests > 0 ? errors / requests : 0,
      unit: 'ratio',
    },
    { name: 'latency_p95_ms', value: latency, unit: 'ms' },
    { name: 'tick_p95_ms', value: tick, unit: 'ms' },
    { name: 'active_sessions', value: activeSessions, unit: 'count' },
    {
      name: 'command_rate',
      value: elapsedSeconds > 0 ? commands / elapsedSeconds : 0,
      unit: 'per_second',
    },
  ];
}

/** The first histogram whose name starts with the prefix. */
function firstHistogram(
  metrics: Metrics,
  prefix: string,
): { count: number; buckets: Record<string, number> } | undefined {
  for (const [name, histogram] of Object.entries(metrics.histograms)) {
    if (name.startsWith(prefix)) return histogram;
  }
  return undefined;
}

/** The alerts that are firing. */
export function evaluateAlerts(
  readings: readonly Measurement[],
  rules: readonly AlertRule[] = ALERT_RULES,
): Alert[] {
  const alerts: Alert[] = [];
  for (const rule of rules) {
    const reading = readings.find((entry) => entry.name === rule.measurement);
    if (!reading) continue;
    const firing =
      rule.comparison === 'above'
        ? reading.value > rule.threshold
        : reading.value < rule.threshold;
    if (!firing) continue;
    alerts.push({
      name: rule.name,
      value: reading.value,
      threshold: rule.threshold,
      severity: rule.severity,
      hint: rule.hint,
    });
  }
  return alerts;
}

/** What the health report is, given the alerts. */
export function statusFor(alerts: readonly Alert[]): HealthReport['status'] {
  if (alerts.some((alert) => alert.severity === 'critical')) return 'unhealthy';
  if (alerts.length > 0) return 'degraded';
  return 'ok';
}

/** The health report. */
export function healthReport(options: {
  metrics: Metrics;
  activeSessions: number;
  elapsedSeconds: number;
  version: string;
  contentBuildId: string;
  assetBuildId?: string | null;
  rules?: readonly AlertRule[];
}): HealthReport {
  const readings = measurements(options.metrics, options.activeSessions, options.elapsedSeconds);
  const alerts = evaluateAlerts(readings, options.rules);
  return {
    status: statusFor(alerts),
    version: options.version,
    contentBuildId: options.contentBuildId,
    assetBuildId: options.assetBuildId ?? null,
    uptimeSeconds: Math.round(options.elapsedSeconds),
    measurements: readings,
    alerts,
    activeSessions: options.activeSessions,
  };
}

/** Escape a value for the dashboard's HTML. */
function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * The dashboard.
 *
 * A page an operator can open, with the **versions in use** at the top -
 * because the first question about a bad server is "what was running?" -
 * and the alerts under them.
 *
 * It is deliberately plain: no framework, no build step, and it works
 * with the JavaScript turned off.
 */
export function dashboardHtml(report: HealthReport): string {
  const rows = report.measurements
    .map(
      (reading) =>
        `      <tr><td>${escapeHtml(reading.name)}</td>` +
        `<td>${reading.value}</td><td>${escapeHtml(reading.unit)}</td></tr>`,
    )
    .join('\n');

  const alerts = report.alerts.length
    ? report.alerts
        .map(
          (alert) =>
            `      <li class="${escapeHtml(alert.severity)}">` +
            `<strong>${escapeHtml(alert.name)}</strong> ` +
            `${alert.value} (over ${alert.threshold}) - ${escapeHtml(alert.hint)}</li>`,
        )
        .join('\n')
    : '      <li class="ok">Nothing is firing.</li>';

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Social Wars Legacy - the server</title>
    <style>
      body { font: 15px/1.5 system-ui, sans-serif; margin: 2rem; color: #222;
             background: #fbfbfd; }
      h1 { font-size: 1.4rem; margin: 0 0 1rem; }
      .status { display: inline-block; padding: 2px 10px; border-radius: 999px;
                font-weight: 600; color: #fff; }
      .ok { background: #2e7d32; } .degraded { background: #ef6c00; }
      .unhealthy { background: #c62828; }
      table { border-collapse: collapse; margin: 1rem 0; }
      td, th { text-align: left; padding: 4px 14px 4px 0; border-bottom: 1px solid #e4e4e8; }
      ul { padding-left: 1.1rem; }
      code { background: #eee; padding: 1px 5px; border-radius: 3px; }
      footer { margin-top: 2rem; color: #666; font-size: 0.9em; }
    </style>
  </head>
  <body>
    <h1>Social Wars Legacy <span class="status ${escapeHtml(report.status)}">${escapeHtml(report.status)}</span></h1>
    <table>
      <tr><td>the server</td><td><code>${escapeHtml(report.version)}</code></td></tr>
      <tr><td>the content</td><td><code>${escapeHtml(report.contentBuildId)}</code></td></tr>
      <tr><td>the assets</td><td><code>${escapeHtml(report.assetBuildId ?? 'unknown')}</code></td></tr>
      <tr><td>up for</td><td>${report.uptimeSeconds} seconds</td></tr>
      <tr><td>the sessions</td><td>${report.activeSessions}</td></tr>
    </table>
    <h2>The measurements</h2>
    <table>
      <tr><th>the measurement</th><th>the value</th><th>the unit</th></tr>
${rows}
    </table>
    <h2>The alerts</h2>
    <ul>
${alerts}
    </ul>
    <footer>The machine-readable report is at <code>/api/health</code>.</footer>
  </body>
</html>
`;
}
