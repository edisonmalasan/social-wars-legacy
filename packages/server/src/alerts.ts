/**
 * Sending the alerts.
 *
 * A report that nobody reads is not an alert. So the alerts are **sent**
 * somewhere: a webhook, which is the one thing every monitoring system
 * and every chat system can receive.
 *
 * ## Only on a change
 *
 * An alert that repeats every second is an alert that gets muted. So a
 * report is sent when the status **changes**, and the sender remembers
 * what it last said.
 *
 * ## Retried
 *
 * A webhook that fails because the network hiccuped must not lose the
 * alert. So the sending is **retried**, with a growing wait between the
 * attempts, and the failure is recorded rather than thrown: a server
 * that cannot reach the alerting system must still serve its players.
 */
import type { HealthReport } from './health.ts';

/** How many times a webhook is tried. */
export const DEFAULT_RETRIES = 3;

/** The wait before the first retry, in milliseconds. */
export const DEFAULT_BACKOFF_MS = 500;

/** Where the alerts go. */
export interface AlertTarget {
  /** The webhook's address. */
  url: string;
  /** An optional label, for the message. */
  label?: string;
}

/** The outcome of a sending. */
export interface SendResult {
  /** Whether the alert was delivered. */
  delivered: boolean;
  /** How many attempts it took. */
  attempts: number;
  /** The last error, when there was one. */
  error?: string;
}

/** Something that sends the alerts. */
export interface AlertSender {
  /** Send a report, if it is worth sending. */
  send(report: HealthReport): Promise<SendResult>;
}

/** The body a webhook receives. */
export interface WebhookBody {
  /** The server's status. */
  status: HealthReport['status'];
  /** The alerts that are firing. */
  alerts: HealthReport['alerts'];
  /** The versions in use. */
  version: string;
  contentBuildId: string;
  assetBuildId: string | null;
  /** How long the server has been up. */
  uptimeSeconds: number;
  /** The measurements. */
  measurements: HealthReport['measurements'];
}

/** The body, for a webhook. */
export function webhookBody(report: HealthReport): WebhookBody {
  return {
    status: report.status,
    alerts: report.alerts,
    version: report.version,
    contentBuildId: report.contentBuildId,
    assetBuildId: report.assetBuildId,
    uptimeSeconds: report.uptimeSeconds,
    measurements: report.measurements,
  };
}

/**
 * A sender that posts to a webhook.
 *
 * The retries wait between the attempts, and the wait **grows**, so a
 * webhook that is down is not hammered.
 */
export class WebhookAlertSender implements AlertSender {
  private readonly target: AlertTarget;
  private readonly fetchImpl: typeof fetch;
  private readonly retries: number;
  private readonly backoffMs: number;

  constructor(options: {
    target: AlertTarget;
    fetchImpl?: typeof fetch;
    retries?: number;
    backoffMs?: number;
  }) {
    this.target = options.target;
    this.fetchImpl = options.fetchImpl ?? fetch;
    this.retries = options.retries ?? DEFAULT_RETRIES;
    this.backoffMs = options.backoffMs ?? DEFAULT_BACKOFF_MS;
  }

  async send(report: HealthReport): Promise<SendResult> {
    let lastError = '';
    for (let attempt = 1; attempt <= this.retries; attempt += 1) {
      try {
        const response = await this.fetchImpl(this.target.url, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(webhookBody(report)),
        });
        if (response.ok) {
          return { delivered: true, attempts: attempt };
        }
        lastError = `the webhook answered ${response.status}`;
      } catch (error) {
        lastError = String(error);
      }
      if (attempt < this.retries) {
        await new Promise((resolve) =>
          setTimeout(resolve, this.backoffMs * attempt),
        );
      }
    }
    return { delivered: false, attempts: this.retries, error: lastError };
  }
}

/**
 * A sender that remembers the last status it reported.
 *
 * It only sends when the status **changes**, so an alert that is still
 * firing does not repeat itself every second - and a server that has
 * recovered says so once.
 */
export class ChangeOnlyAlertSender implements AlertSender {
  private readonly inner: AlertSender;
  private lastStatus: HealthReport['status'] | null = null;

  constructor(inner: AlertSender) {
    this.inner = inner;
  }

  /** The status it last reported. */
  get reported(): HealthReport['status'] | null {
    return this.lastStatus;
  }

  async send(report: HealthReport): Promise<SendResult> {
    if (report.status === this.lastStatus) {
      // Nothing has changed, so there is nothing to say.
      return { delivered: true, attempts: 0 };
    }
    this.lastStatus = report.status;
    return this.inner.send(report);
  }
}
