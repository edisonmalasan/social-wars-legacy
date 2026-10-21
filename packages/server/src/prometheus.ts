/**
 * The metrics, in the Prometheus text format.
 *
 * The registry already holds the series in the shape a time-series
 * database wants: a name, some labels and a value. This turns that into
 * the text format, so any scraper can read it, and the **exported**
 * metrics are what make the alerts possible — an alert that cannot see
 * a regression cannot fire on one.
 *
 * The format is the one every scraper understands:
 *
 * ```
 * # TYPE http_requests_total counter
 * http_requests_total{method="GET",path="/health"} 12
 * ```
 */
import type { Metrics } from './observability.ts';

/** The metrics' names, and what they are. */
const TYPES: Record<string, 'counter' | 'gauge' | 'histogram'> = {
  http_requests_total: 'counter',
  http_errors_total: 'counter',
  commands_total: 'counter',
  active_sessions: 'gauge',
};

/**
 * A series' name and its labels.
 *
 * The registry's keys are `name{key=value,key=value}`, so the labels
 * have to be taken apart again to be written out.
 */
export function parseSeries(key: string): { name: string; labels: [string, string][] } {
  const open = key.indexOf('{');
  if (open < 0) return { name: key, labels: [] };
  const name = key.slice(0, open);
  const body = key.slice(open + 1, key.lastIndexOf('}'));
  const labels: [string, string][] = [];
  for (const part of body.split(',')) {
    const equals = part.indexOf('=');
    if (equals < 0) continue;
    labels.push([
      part.slice(0, equals).trim(),
      part.slice(equals + 1).trim().replace(/^"|"$/g, ''),
    ]);
  }
  return { name, labels };
}

/** A label's value, escaped for the text format. */
function escapeLabel(value: string): string {
  return value.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, '\\n');
}

/**
 * The metrics, in the text format.
 *
 * The histograms are written as a **summary** rather than as buckets,
 * because the registry's histograms are cumulative counts over the
 * buckets and the summary is what a dashboard wants: the count, the sum
 * and the range.
 */
export function prometheusText(metrics: Metrics): string {
  const lines: string[] = [];

  for (const [key, value] of Object.entries(metrics.counters).sort()) {
    const { name, labels } = parseSeries(key);
    lines.push(`# TYPE ${name} ${TYPES[name] ?? 'counter'}`);
    lines.push(`${name}${renderLabels(labels)} ${value}`);
  }

  for (const [key, value] of Object.entries(metrics.gauges).sort()) {
    const { name, labels } = parseSeries(key);
    lines.push(`# TYPE ${name} ${TYPES[name] ?? 'gauge'}`);
    lines.push(`${name}${renderLabels(labels)} ${value}`);
  }

  for (const [key, histogram] of Object.entries(metrics.histograms).sort()) {
    const { name, labels } = parseSeries(key);
    lines.push(`# TYPE ${name} summary`);
    lines.push(`${name}_count${renderLabels(labels)} ${histogram.count}`);
    lines.push(`${name}_sum${renderLabels(labels)} ${histogram.sum}`);
    lines.push(`${name}_min${renderLabels(labels)} ${histogram.min}`);
    lines.push(`${name}_max${renderLabels(labels)} ${histogram.max}`);
  }

  return lines.length > 0 ? `${lines.join('\n')}\n` : '';
}

/** The labels, written out. */
function renderLabels(labels: [string, string][]): string {
  if (labels.length === 0) return '';
  const rendered = labels
    .map(([key, value]) => `${key}="${escapeLabel(value)}"`)
    .join(',');
  return `{${rendered}}`;
}
