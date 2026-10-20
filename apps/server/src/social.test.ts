import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { framePayload, SERVER_KEYS } from '@swl/protocol';
import { AllianceService, type AllianceUser } from '@swl/server';

import { handleSocialRequest, type SocialOptions } from './social.ts';

const NOW = 1_700_000_000;

const alice: AllianceUser = { id: 'alice', name: 'Alice', country: 'uk' };
const bob: AllianceUser = { id: 'bob', name: 'Bob', country: 'uk' };

function options(): SocialOptions {
  const alliances = new AllianceService([], [alice, bob]);
  return {
    alliances,
    now: () => NOW,
    resolveUser: (userId) => {
      if (userId === 'alice') return { id: 'alice', name: 'Alice', country: 'uk' };
      if (userId === 'bob') return { id: 'bob', name: 'Bob', country: 'uk' };
      return null;
    },
  };
}

/** A service request, with the client's envelope. */
function serviceRequest(
  method: string,
  params: Record<string, unknown>,
  key: string = SERVER_KEYS.current,
): {
  method: string;
  path: string;
  headers: Record<string, string | undefined>;
  body: string;
} {
  const payload = JSON.stringify({ userId: 'alice', ...params });
  const frame = framePayload(payload, key);
  return {
    method: 'POST',
    path: `/alliance/?method=${method}&USERID=alice`,
    headers: {
      'content-type': 'application/x-www-form-urlencoded',
      data: frame,
    },
    body: `data=${encodeURIComponent(frame)}`,
  };
}

describe('the social endpoints', () => {
  it('ignores a path that is not a social one', () => {
    assert.equal(handleSocialRequest({ method: 'POST', path: '/health', headers: {}, body: '' }, options()), null);
  });

  it('creates an alliance', () => {
    const response = handleSocialRequest(
      serviceRequest('alliance-create', { title: 'The Brigade' }),
      options(),
    );
    assert.ok(response);
    assert.equal(response.status, 200);
    const body = JSON.parse(response.body);
    assert.equal(body.success, true);
    assert.equal(body.data.title, 'The Brigade');
  });

  it('answers with the client error NUMBER', () => {
    // The SAME service, so the second create really is a duplicate.
    const context = options();
    const response = handleSocialRequest(
      serviceRequest('alliance-create', { title: 'The Brigade' }),
      context,
    );
    assert.ok(response);
    const body = JSON.parse(response.body);
    assert.equal(body.success, true);

    // A second alliance with the same title and owner fails with 100.
    const second = handleSocialRequest(
      serviceRequest('alliance-create', { title: 'the brigade' }),
      context,
    );
    assert.ok(second);
    const secondBody = JSON.parse(second.body);
    assert.equal(secondBody.success, false);
    assert.equal(secondBody.error, 100);
  });

  it('refuses a body that is not framed', () => {
    const response = handleSocialRequest(
      {
        method: 'POST',
        path: '/alliance/?method=alliance-create',
        headers: { data: '{"userId":"alice"}' },
        body: '',
      },
      options(),
    );
    assert.ok(response);
    assert.equal(response.status, 400);
    assert.equal(JSON.parse(response.body).success, false);
  });

  it('refuses a body signed with the wrong key', () => {
    const response = handleSocialRequest(
      serviceRequest('alliance-create', { title: 'X' }, 'not-a-real-key'),
      options(),
    );
    assert.ok(response);
    assert.equal(response.status, 400);
    assert.equal(JSON.parse(response.body).success, false);
  });

  it('accepts either server key', () => {
    for (const key of [SERVER_KEYS.current, SERVER_KEYS.legacy]) {
      const response = handleSocialRequest(
        serviceRequest('alliance-create', { title: `Brigade ${key}` }, key),
        options(),
      );
      assert.ok(response);
      assert.equal(JSON.parse(response.body).success, true, `the ${key} key was refused`);
    }
  });

  it('refuses an unknown variant', () => {
    const response = handleSocialRequest(
      serviceRequest('not-a-variant', {}),
      options(),
    );
    assert.ok(response);
    assert.equal(response.status, 400);
  });

  it('runs the join request flow end to end', () => {
    const context = options();
    const created = handleSocialRequest(
      serviceRequest('alliance-create', { title: 'Brigade' }),
      context,
    );
    assert.ok(created);
    const alliance = JSON.parse(created.body).data;

    // Another player asks to join.
    const payload = JSON.stringify({ userId: 'bob', allianceId: alliance.id });
    const frame = framePayload(payload, SERVER_KEYS.current);
    const sent = handleSocialRequest(
      {
        method: 'POST',
        path: '/alliance/?method=join-request-send&USERID=bob',
        headers: { data: frame },
        body: `data=${encodeURIComponent(frame)}`,
      },
      context,
    );
    assert.ok(sent);
    assert.equal(JSON.parse(sent.body).success, true);

    // The owner processes it.
    const processed = handleSocialRequest(
      serviceRequest('join-request-process', {
        allianceId: alliance.id,
        memberId: 'bob',
        status: 'accept',
      }),
      context,
    );
    assert.ok(processed);
    assert.equal(JSON.parse(processed.body).success, true);

    const members = handleSocialRequest(
      serviceRequest('member-list', { allianceId: alliance.id, members: -1 }),
      context,
    );
    assert.ok(members);
    assert.equal(JSON.parse(members.body).data.length, 2);
  });

  it('answers the betting endpoints with a typed failure when the service is not wired', () => {
    const response = handleSocialRequest(
      {
        method: 'POST',
        path: '/bets/get_bets_list.php',
        headers: {},
        body: '',
      },
      options(),
    );
    assert.ok(response);
    assert.equal(response.status, 501);
  });

  it('refuses a GET', () => {
    const response = handleSocialRequest(
      { method: 'GET', path: '/alliance/?method=alliance-list', headers: {}, body: '' },
      options(),
    );
    assert.ok(response);
    assert.equal(response.status, 405);
  });
});
