import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  ChangeOnlyAlertSender,
  WebhookAlertSender,
  webhookBody,
  type SendResult,
} from './alerts.ts';
import type { HealthReport } from './health.ts';

function report(status: HealthReport['status'] = 'unhealthy'): HealthReport {
  return {
    status,
    version: '0.1.0',
    contentBuildId: 'abc123',
    assetBuildId: 'def456',
    uptimeSeconds: 120,
    measurements: [
      { name: 'error_rate', value: 0.5, unit: 'ratio' },
      { name: 'latency_p95_ms', value: 900, unit: 'ms' },
    ],
    alerts: [
      {
        name: 'error-rate',
        value: 0.5,
        threshold: 0.1,
        severity: 'critical',
        hint: 'a tenth of the requests are failing',
      },
    ],
    activeSessions: 3,
  };
}

describe('the webhook body', () => {
  it('carries the report', () => {
    const body = webhookBody(report());
    assert.equal(body.status, 'unhealthy');
    assert.equal(body.alerts.length, 1);
    assert.equal(body.version, '0.1.0');
    assert.equal(body.contentBuildId, 'abc123');
    assert.equal(body.assetBuildId, 'def456');
    assert.equal(body.measurements.length, 2);
  });
});

describe('the webhook sender', () => {
  it('delivers', async () => {
    let sent: { url: string; body: string } | null = null;
    const sender = new WebhookAlertSender({
      target: { url: 'https://alerts.example/hook' },
      fetchImpl: async (url, init) => {
        sent = { url: String(url), body: String(init?.body) };
        return new Response('{}', { status: 200 });
      },
    });

    const result = await sender.send(report());
    assert.equal(result.delivered, true);
    assert.equal(result.attempts, 1);
    assert.ok(sent);
    assert.equal((sent as unknown as { url: string }).url, 'https://alerts.example/hook');
  });

  it('retries when the webhook fails', async () => {
    let attempts = 0;
    const sender = new WebhookAlertSender({
      target: { url: 'https://alerts.example/hook' },
      retries: 3,
      backoffMs: 1,
      fetchImpl: async () => {
        attempts += 1;
        return new Response('{}', { status: 500 });
      },
    });

    const result = await sender.send(report());
    assert.equal(result.delivered, false);
    assert.equal(attempts, 3);
    assert.equal(result.attempts, 3);
    assert.ok(result.error);
  });

  it('retries when the network fails', async () => {
    let attempts = 0;
    const sender = new WebhookAlertSender({
      target: { url: 'https://alerts.example/hook' },
      retries: 2,
      backoffMs: 1,
      fetchImpl: async () => {
        attempts += 1;
        throw new Error('offline');
      },
    });

    const result = await sender.send(report());
    assert.equal(result.delivered, false);
    assert.equal(attempts, 2);
  });

  it('succeeds on a later attempt', async () => {
    let attempts = 0;
    const sender = new WebhookAlertSender({
      target: { url: 'https://alerts.example/hook' },
      retries: 3,
      backoffMs: 1,
      fetchImpl: async () => {
        attempts += 1;
        return new Response('{}', { status: attempts < 2 ? 500 : 200 });
      },
    });

    const result = await sender.send(report());
    assert.equal(result.delivered, true);
    assert.equal(result.attempts, 2);
  });
});

describe('the change-only sender', () => {
  it('sends when the status changes', async () => {
    const sent: HealthReport[] = [];
    const inner = {
      send: async (value: HealthReport): Promise<SendResult> => {
        sent.push(value);
        return { delivered: true, attempts: 1 };
      },
    };
    const sender = new ChangeOnlyAlertSender(inner);

    await sender.send(report('ok'));
    assert.equal(sent.length, 1);

    // The same status: nothing to say.
    await sender.send(report('ok'));
    assert.equal(sent.length, 1);

    // It got worse: say so.
    await sender.send(report('unhealthy'));
    assert.equal(sent.length, 2);

    // And it recovered.
    await sender.send(report('ok'));
    assert.equal(sent.length, 3);
  });

  it('remembers what it reported', async () => {
    const inner = {
      send: async (): Promise<SendResult> => ({ delivered: true, attempts: 1 }),
    };
    const sender = new ChangeOnlyAlertSender(inner);
    assert.equal(sender.reported, null);
    await sender.send(report('degraded'));
    assert.equal(sender.reported, 'degraded');
  });
});
