import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { Metrics } from './observability.ts';
import { parseSeries, prometheusText } from './prometheus.ts';

describe('the series', () => {
  it('are taken apart into a name and its labels', () => {
    const { name, labels } = parseSeries('http_requests_total{method=GET,path=/health}');
    assert.equal(name, 'http_requests_total');
    assert.deepEqual(labels, [
      ['method', 'GET'],
      ['path', '/health'],
    ]);
  });

  it('are a bare name when there are no labels', () => {
    const { name, labels } = parseSeries('active_sessions');
    assert.equal(name, 'active_sessions');
    assert.deepEqual(labels, []);
  });
});

describe('the text format', () => {
  it('writes the counters with their type', () => {
    const metrics = new Metrics();
    metrics.increment('http_requests_total', { method: 'GET', path: '/health' });
    const text = prometheusText(metrics);
    assert.match(text, /# TYPE http_requests_total counter/);
    assert.match(text, /http_requests_total\{method="GET",path="\/health"\} 1/);
  });

  it('writes the gauges', () => {
    const metrics = new Metrics();
    metrics.gauge('active_sessions', 4);
    const text = prometheusText(metrics);
    assert.match(text, /# TYPE active_sessions gauge/);
    assert.match(text, /active_sessions 4/);
  });

  it('writes the histograms as a summary', () => {
    const metrics = new Metrics();
    metrics.observe('http_request_duration_ms', 12, { path: '/health' });
    const text = prometheusText(metrics);
    assert.match(text, /# TYPE http_request_duration_ms summary/);
    assert.match(text, /http_request_duration_ms_count\{path="\/health"\} 1/);
    assert.match(text, /http_request_duration_ms_sum\{path="\/health"\} 12/);
  });

  it('escapes the label values', () => {
    const metrics = new Metrics();
    metrics.increment('http_requests_total', { path: '/a"b' });
    const text = prometheusText(metrics);
    assert.match(text, /path="\/a\\"b"/);
  });

  it('is empty when there is nothing', () => {
    assert.equal(prometheusText(new Metrics()), '');
  });
});
