import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { Metrics } from './observability.ts';
import {
  ALERT_RULES,
  evaluateAlerts,
  healthReport,
  measurements,
  percentile,
  statusFor,
  type Measurement,
} from './health.ts';

describe('the percentile', () => {
  it('is the bucket it falls in', () => {
    const histogram = {
      count: 100,
      buckets: { '10': 50, '100': 90, '1000': 100 },
    };
    // Half the observations are under ten.
    assert.equal(percentile(histogram, 0.5), 10);
    // Nine in ten are under a hundred.
    assert.equal(percentile(histogram, 0.95), 1000);
  });

  it('is nothing when there is nothing', () => {
    assert.equal(percentile(undefined, 0.95), 0);
    assert.equal(percentile({ count: 0, buckets: {} }, 0.95), 0);
  });
});

describe('the measurements', () => {
  it('count the error rate', () => {
    const metrics = new Metrics();
    metrics.increment('http_requests_total', { path: '/a', status: '200' });
    metrics.increment('http_requests_total', { path: '/a', status: '200' });
    metrics.increment('http_errors_total', { path: '/a', status: '500' });

    const readings = measurements(metrics, 3, 60);
    const errorRate = readings.find((entry) => entry.name === 'error_rate');
    assert.ok(errorRate);
    // One error in two requests.
    assert.equal(errorRate!.value, 0.5);
    assert.equal(errorRate!.unit, 'ratio');
  });

  it('count the active sessions', () => {
    const readings = measurements(new Metrics(), 7, 60);
    const sessions = readings.find((entry) => entry.name === 'active_sessions');
    assert.equal(sessions?.value, 7);
  });

  it('count the command rate', () => {
    const metrics = new Metrics();
    metrics.increment('commands_total', { name: 'buy' });
    metrics.increment('commands_total', { name: 'buy' });
    const readings = measurements(metrics, 0, 10);
    const rate = readings.find((entry) => entry.name === 'command_rate');
    assert.equal(rate?.value, 0.2);
  });
});

describe('the alerts', () => {
  const readings: Measurement[] = [
    { name: 'error_rate', value: 0.5, unit: 'ratio' },
    { name: 'latency_p95_ms', value: 100, unit: 'ms' },
    { name: 'tick_p95_ms', value: 10, unit: 'ms' },
  ];

  it('fire when the measurement is over the threshold', () => {
    const alerts = evaluateAlerts(readings);
    const errorRate = alerts.find((alert) => alert.name === 'error-rate');
    assert.ok(errorRate);
    assert.equal(errorRate!.severity, 'critical');
    assert.equal(errorRate!.value, 0.5);
  });

  it('do not fire when it is under', () => {
    const alerts = evaluateAlerts([
      { name: 'error_rate', value: 0, unit: 'ratio' },
      { name: 'latency_p95_ms', value: 10, unit: 'ms' },
      { name: 'tick_p95_ms', value: 1, unit: 'ms' },
    ]);
    assert.deepEqual(alerts, []);
  });

  it('say what to do about it', () => {
    const alerts = evaluateAlerts(readings);
    for (const alert of alerts) {
      assert.ok(alert.hint.length > 10, `${alert.name} says nothing`);
    }
  });

  it('have their thresholds written down', () => {
    assert.ok(ALERT_RULES.length > 0);
    for (const rule of ALERT_RULES) {
      assert.ok(rule.name.length > 0);
      assert.ok(rule.measurement.length > 0);
      assert.equal(typeof rule.threshold, 'number');
      assert.ok(['warning', 'critical'].includes(rule.severity));
    }
  });
});

describe('the status', () => {
  it('is ok when nothing is firing', () => {
    assert.equal(statusFor([]), 'ok');
  });

  it('is degraded on a warning', () => {
    assert.equal(
      statusFor([
        {
          name: 'w',
          value: 1,
          threshold: 0,
          severity: 'warning',
          hint: 'x',
        },
      ]),
      'degraded',
    );
  });

  it('is unhealthy on a critical', () => {
    assert.equal(
      statusFor([
        {
          name: 'c',
          value: 1,
          threshold: 0,
          severity: 'critical',
          hint: 'x',
        },
      ]),
      'unhealthy',
    );
  });
});

describe('the health report', () => {
  it('carries the versions in use', () => {
    const report = healthReport({
      metrics: new Metrics(),
      activeSessions: 2,
      elapsedSeconds: 120,
      version: '0.1.0',
      contentBuildId: 'abc123',
      assetBuildId: 'def456',
    });
    assert.equal(report.status, 'ok');
    assert.equal(report.version, '0.1.0');
    assert.equal(report.contentBuildId, 'abc123');
    assert.equal(report.assetBuildId, 'def456');
    assert.equal(report.uptimeSeconds, 120);
    assert.equal(report.activeSessions, 2);
  });

  it('is unhealthy when a critical alert is firing', () => {
    const metrics = new Metrics();
    metrics.increment('http_requests_total', { path: '/a', status: '500' });
    metrics.increment('http_errors_total', { path: '/a', status: '500' });

    const report = healthReport({
      metrics,
      activeSessions: 0,
      elapsedSeconds: 60,
      version: '0.1.0',
      contentBuildId: 'abc123',
    });
    assert.equal(report.status, 'unhealthy');
    assert.ok(report.alerts.length > 0);
  });
});
