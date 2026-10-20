/**
 * The social layer over HTTP.
 *
 * The client calls the alliance and betting services with the **same
 * envelope as `command.php`**: a `data` field holding
 * `<64 hex>;<json>`, where the hex is `HMAC-SHA256(SERVER_KEY, json)`.
 * (`managers/ServiceManager.as:44-52`.)
 *
 * The URL carries the variant:
 *
 * ```
 * alliance/?method=alliance-create&USERID=<session>&user_key=<key>
 * bets/get_bets_list.php
 * bets/get_bet_detail.php
 * bets/set_bet.php
 * ```
 *
 * The response is read with `Crypto.getHashAndPayload`, so it may be
 * framed or plain, and the client takes the whole object when it has a
 * `success` property and the `data` property otherwise
 * (`managers/ServiceManager.as:78-92`).
 *
 * So the answers are:
 *
 * ```json
 * { "success": true, "data": { ... } }
 * { "success": false, "error": 204 }
 * ```
 *
 * The error is the client's **number**, because the client switches on
 * it.
 */
import { ACCEPTED_KEYS, parseFrame, verifyFrameAny } from '@swl/protocol';
import type { AllianceService, MarketplaceResult, MarketplaceService } from '@swl/server';

import type { AppRequest, AppResponse } from './app.ts';

/** The service variants, as the client's `Config.SERVICE_*` spell them. */
export const ALLIANCE_METHODS = [
  'alliance-create',
  'alliance-update',
  'alliance-info',
  'alliance-list',
  'alliance-find',
  'join-request-send',
  'join-request-list',
  'join-request-process',
  'member-list',
  'member-leave',
  'member-kick',
] as const;

export type AllianceMethod = (typeof ALLIANCE_METHODS)[number];

/** The betting endpoints. */
export const BETTING_PATHS = [
  '/bets/get_bets_list.php',
  '/bets/get_bet_detail.php',
  '/bets/set_bet.php',
] as const;

/** What the social layer needs. */
export interface SocialOptions {
  /** The alliance service. */
  alliances?: AllianceService;
  /** The marketplace service, for the three betting endpoints. */
  marketplace?: MarketplaceService;
  /** The clock, in seconds. */
  now: () => number;
  /** Resolves a legacy `USERID` to a player, for the service's own user. */
  resolveUser?: (userId: string | undefined) => { id: string; name: string; country: string } | null;
  /** The player's level, for the marketplace's level floor. */
  level?: number;
  /** The player's cash, for the marketplace's bids. */
  cash?: number;
}

/** The service's answer. */
export interface ServiceAnswer {
  success: boolean;
  data?: unknown;
  error?: number;
}

/** A JSON response. */
function json(status: number, body: unknown): AppResponse {
  return {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8' },
    body: JSON.stringify(body),
  };
}

/**
 * The service's parameters, from the request.
 *
 * The body is the framed JSON, and the query string carries the variant
 * and the legacy `USERID`.
 */
function serviceParams(request: AppRequest): {
  params: Record<string, unknown>;
  error?: string;
} {
  const fields: Record<string, string> = {};
  for (const [key, value] of Object.entries(request.headers)) {
    if (value !== undefined) fields[key.toLowerCase()] = value;
  }
  const at = request.path.indexOf('?');
  let query: Record<string, string> = {};
  if (at >= 0) {
    for (const pair of request.path.slice(at + 1).split('&')) {
      if (pair === '') continue;
      const eq = pair.indexOf('=');
      const key = eq < 0 ? pair : pair.slice(0, eq);
      const value = eq < 0 ? '' : pair.slice(eq + 1);
      try {
        query[decodeURIComponent(key)] = decodeURIComponent(value.replace(/\+/g, ' '));
      } catch {
        query[key] = value;
      }
    }
  }

  const data = fields['data'];
  if (!data) return { params: query, error: 'missing-data' };

  const parsed = parseFrame(data);
  if (!parsed.framed) return { params: query, error: 'malformed-framing' };
  if (verifyFrameAny(data, ACCEPTED_KEYS) === null) {
    return { params: query, error: 'bad-signature' };
  }
  try {
    const payload = JSON.parse(parsed.payload) as unknown;
    if (typeof payload !== 'object' || payload === null || Array.isArray(payload)) {
      return { params: query, error: 'malformed-payload' };
    }
    return { params: { ...query, ...(payload as Record<string, unknown>) } };
  } catch {
    return { params: query, error: 'malformed-payload' };
  }
}

/** Read a parameter as a string. */
function str(params: Record<string, unknown>, key: string): string | undefined {
  const value = params[key];
  if (typeof value === 'string') return value;
  if (typeof value === 'number') return String(value);
  return undefined;
}

/** Read a parameter as a number. */
function num(params: Record<string, unknown>, key: string): number | undefined {
  const value = params[key];
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return undefined;
}

/**
 * Handle a social service request.
 *
 * Returns null when the path is not a social endpoint, so the caller can
 * carry on.
 */
export function handleSocialRequest(
  request: AppRequest,
  context: SocialOptions,
): AppResponse | null {
  const path = request.path.split('?')[0] ?? request.path;
  const isAlliance = path === '/alliance/' || path === '/alliance';
  const isBetting = (BETTING_PATHS as readonly string[]).includes(path);
  if (!isAlliance && !isBetting) return null;

  if (request.method !== 'POST') {
    return json(405, { success: false, error: 2 });
  }

  if (isBetting && !context.marketplace) {
    // The service is not wired, and saying so is more useful than
    // complaining about the body.
    return json(501, { success: false, error: 1 });
  }

  const { params, error } = serviceParams(request);
  if (error) {
    return json(400, { success: false, error: error === 'bad-signature' ? 3 : 2 });
  }

  if (isAlliance) {
    const method = str(params, 'method');
    if (!method || !(ALLIANCE_METHODS as readonly string[]).includes(method)) {
      return json(400, { success: false, error: 1 });
    }
    if (!context.alliances) {
      return json(501, { success: false, error: 1 });
    }
    return json(200, runAlliance(context.alliances, method as AllianceMethod, params, context));
  }

  // The three betting endpoints are the marketplace's.
  const marketplace = context.marketplace;
  if (!marketplace) {
    return json(501, { success: false, error: 1 });
  }
  const now = context.now();
  const userId = str(params, 'user_id') ?? str(params, 'userId');

  if (path === '/bets/get_bets_list.php') {
    const result = marketplace.getBetsList(
      { userId: userId ?? '', level: num(params, 'level') ?? context.level ?? 0 },
      now,
    );
    return json(200, marketplaceAnswer(result));
  }

  if (path === '/bets/get_bet_detail.php') {
    const result = marketplace.getBetDetail(
      {
        userId: userId ?? '',
        uuid: str(params, 'uuid') ?? '',
        checkFinish: params['checkFinish'] === true || params['checkFinish'] === 'true' || params['checkFinish'] === 1,
      },
      now,
    );
    return json(200, marketplaceAnswer(result));
  }

  // `/bets/set_bet.php`
  const result = marketplace.setBet(
    {
      userId: userId ?? '',
      uuid: str(params, 'uuid') ?? '',
      round: num(params, 'round') ?? 0,
      bet: num(params, 'bet') ?? 0,
      clientId: str(params, 'client_id'),
      sessionId: str(params, 'session_id'),
    },
    now,
  );
  return json(200, marketplaceAnswer(result));
}

/** The marketplace's answer, in the client's shape. */
function marketplaceAnswer(result: MarketplaceResult): ServiceAnswer {
  if (!result.success) return { success: false, error: result.error ?? 1 };
  return {
    success: true,
    data: {
      ...(result.bets !== undefined ? { bets: result.bets } : {}),
      ...(result.detail !== undefined ? { detail: result.detail } : {}),
      ...(result.betResult !== undefined ? { betResult: result.betResult } : {}),
      ...(result.cashCost !== undefined ? { cashCost: result.cashCost } : {}),
      ...(result.settlements !== undefined ? { settlements: result.settlements } : {}),
    },
  };
}

/** Run one alliance variant. */
function runAlliance(
  service: AllianceService,
  method: AllianceMethod,
  params: Record<string, unknown>,
  context: SocialOptions,
): ServiceAnswer {
  const userId = str(params, 'userId');
  const user = context.resolveUser?.(userId) ?? undefined;

  const shared = {
    userId,
    user: user
      ? { id: user.id, name: user.name, country: user.country }
      : undefined,
  };

  switch (method) {
    case 'alliance-create': {
      const result = service.create(
        {
          ...shared,
          title: str(params, 'title'),
          description: str(params, 'description'),
          bestUnit: num(params, 'bestUnit'),
        },
        context.now(),
      );
      return answer(result.success, result.error, result.alliance);
    }
    case 'alliance-update': {
      const result = service.update({
        ...shared,
        allianceId: str(params, 'allianceId'),
        description: str(params, 'description'),
      });
      return answer(result.success, result.error, result.alliance);
    }
    case 'alliance-info': {
      const result = service.info({
        ...shared,
        allianceId: str(params, 'allianceId'),
        members: num(params, 'members'),
      });
      return answer(result.success, result.error, result.alliance);
    }
    case 'alliance-list': {
      const result = service.list(shared);
      return answer(result.success, result.error, result.alliances);
    }
    case 'alliance-find': {
      const result = service.find({
        ...shared,
        title: str(params, 'title'),
        userCountry: str(params, 'userCountry'),
        openOnly: params['openOnly'] === true || params['openOnly'] === 'true' || params['openOnly'] === 1,
        pageNo: num(params, 'pageNo'),
        perPage: num(params, 'perPage'),
      });
      return answer(result.success, result.error, result.alliances);
    }
    case 'join-request-send': {
      const result = service.joinRequestSend(
        {
          ...shared,
          targetAllianceId: str(params, 'allianceId') ?? str(params, 'targetAllianceId'),
          bestUnit: num(params, 'bestUnit'),
        },
        context.now(),
      );
      return answer(result.success, result.error, undefined);
    }
    case 'join-request-list': {
      const result = service.joinRequestList({
        ...shared,
        allianceId: str(params, 'allianceId'),
      });
      return answer(result.success, result.error, result.joinRequests);
    }
    case 'join-request-process': {
      const status = str(params, 'status');
      const result = service.joinRequestProcess({
        ...shared,
        allianceId: str(params, 'allianceId'),
        memberId: str(params, 'memberId'),
        status: status === 'accept' ? 'accept' : 'decline',
      });
      return answer(result.success, result.error, undefined);
    }
    case 'member-list': {
      const result = service.memberList({
        ...shared,
        allianceId: str(params, 'allianceId'),
        members: num(params, 'members'),
        idsOnly: params['idsOnly'] === true || params['idsOnly'] === 'true' || params['idsOnly'] === 1,
      });
      return answer(result.success, result.error, result.members);
    }
    case 'member-leave': {
      const result = service.memberLeave(shared);
      return answer(result.success, result.error, undefined);
    }
    case 'member-kick': {
      const result = service.memberKick({
        ...shared,
        allianceId: str(params, 'allianceId'),
        memberId: str(params, 'memberId'),
      });
      return answer(result.success, result.error, undefined);
    }
  }
}

/** The answer's shape. */
function answer(success: boolean, error: number | undefined, data: unknown): ServiceAnswer {
  if (!success) return { success: false, error: error ?? 1 };
  return { success: true, data };
}
