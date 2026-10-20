import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  ALLIANCE_ERRORS,
  AllianceService,
  DEFAULT_ALLIANCE_RULES,
  allianceBonusTier,
  type AllianceUser,
} from './alliance.ts';

const NOW = 1_700_000_000;

const alice: AllianceUser = { id: 'alice', name: 'Alice', country: 'uk' };
const bob: AllianceUser = { id: 'bob', name: 'Bob', country: 'uk' };
const carol: AllianceUser = { id: 'carol', name: 'Carol', country: 'fr' };

function service(): AllianceService {
  return new AllianceService([], [alice, bob, carol]);
}

describe('the error vocabulary', () => {
  it('is the client own, exactly', () => {
    // The client switches on these numbers, so they must be exactly these.
    assert.equal(ALLIANCE_ERRORS.ERR_SYS_UNKNOWN, 1);
    assert.equal(ALLIANCE_ERRORS.ERR_SYS_MISSING_ARGS, 2);
    assert.equal(ALLIANCE_ERRORS.ERR_SYS_INVALID_ARG, 3);
    assert.equal(ALLIANCE_ERRORS.ERR_SYS_USER_NOT_EXIST, 4);
    assert.equal(ALLIANCE_ERRORS.ERR_ALLIANCE_EXISTS, 100);
    assert.equal(ALLIANCE_ERRORS.ERR_ALLIANCE_NOT_EXISTS, 101);
    assert.equal(ALLIANCE_ERRORS.ERR_ALLIANCE_CREATE, 102);
    assert.equal(ALLIANCE_ERRORS.ERR_ALLIANCE_OWNER_SWITCH, 103);
    assert.equal(ALLIANCE_ERRORS.ERR_MEMBER_NOT_OWNER, 200);
    assert.equal(ALLIANCE_ERRORS.ERR_MEMBER_BELONGS, 201);
    assert.equal(ALLIANCE_ERRORS.ERR_MEMBER_NOT_BELONGS, 202);
    assert.equal(ALLIANCE_ERRORS.ERR_MEMBER_KICK, 203);
    assert.equal(ALLIANCE_ERRORS.ERR_MEMBER_LIMIT, 204);
    assert.equal(ALLIANCE_ERRORS.ERR_WRONG_COUNTRY, 205);
    assert.equal(ALLIANCE_ERRORS.ERR_JOIN_SEND, 300);
    assert.equal(ALLIANCE_ERRORS.ERR_JOIN_PROCESS, 301);
    assert.equal(ALLIANCE_ERRORS.ERR_JOIN_NOT_EXIST, 302);
  });

  it('has seventeen codes', () => {
    assert.equal(Object.keys(ALLIANCE_ERRORS).length, 17);
  });
});

describe('creating an alliance', () => {
  it('makes one, with the creator as its owner and only member', () => {
    const alliances = service();
    const result = alliances.create({ user: alice, title: 'The Brigade' }, NOW);
    assert.equal(result.success, true);
    assert.equal(result.alliance?.title, 'The Brigade');
    assert.equal(result.alliance?.ownerId, 'alice');
    assert.equal(result.alliance?.members.length, 1);
    assert.equal(result.alliance?.country, 'uk');
  });

  it('refuses a second alliance with the same title and owner', () => {
    const alliances = service();
    alliances.create({ user: alice, title: 'The Brigade' }, NOW);
    const second = alliances.create({ user: alice, title: 'the brigade' }, NOW);
    assert.equal(second.success, false);
    assert.equal(second.error, ALLIANCE_ERRORS.ERR_ALLIANCE_EXISTS);
  });

  it('refuses an alliance with no title', () => {
    const result = service().create({ user: alice, title: '  ' }, NOW);
    assert.equal(result.error, ALLIANCE_ERRORS.ERR_SYS_MISSING_ARGS);
  });

  it('refuses an unknown player', () => {
    const result = service().create({ userId: 'nobody', title: 'X' }, NOW);
    assert.equal(result.error, ALLIANCE_ERRORS.ERR_SYS_USER_NOT_EXIST);
  });
});

describe('updating an alliance', () => {
  it('lets the owner change the description', () => {
    const alliances = service();
    const created = alliances.create({ user: alice, title: 'Brigade' }, NOW);
    const result = alliances.update({
      user: alice,
      allianceId: created.alliance!.id,
      description: 'We are the best',
    });
    assert.equal(result.success, true);
    assert.equal(result.alliance?.description, 'We are the best');
  });

  it('refuses a member who is not the owner', () => {
    const alliances = service();
    const created = alliances.create({ user: alice, title: 'Brigade' }, NOW);
    const result = alliances.update({
      user: bob,
      allianceId: created.alliance!.id,
      description: 'nope',
    });
    assert.equal(result.error, ALLIANCE_ERRORS.ERR_MEMBER_NOT_OWNER);
  });
});

describe('joining an alliance', () => {
  function withAlliance(): { alliances: AllianceService; id: string } {
    const alliances = service();
    const created = alliances.create({ user: alice, title: 'Brigade' }, NOW);
    return { alliances, id: created.alliance!.id };
  }

  it('takes a request and processes it', () => {
    const { alliances, id } = withAlliance();
    const sent = alliances.joinRequestSend({ user: bob, targetAllianceId: id }, NOW);
    assert.equal(sent.success, true);

    const listed = alliances.joinRequestList({ user: alice, allianceId: id });
    assert.equal(listed.joinRequests?.length, 1);
    assert.equal(listed.joinRequests?.[0]?.memberId, 'bob');

    const processed = alliances.joinRequestProcess({
      user: alice,
      allianceId: id,
      memberId: 'bob',
      status: 'accept',
    });
    assert.equal(processed.success, true);
    const members = alliances.memberList({ user: alice, allianceId: id });
    assert.equal(members.members?.length, 2);
  });

  it('declines a request without adding the member', () => {
    const { alliances, id } = withAlliance();
    alliances.joinRequestSend({ user: bob, targetAllianceId: id }, NOW);
    alliances.joinRequestProcess({
      user: alice,
      allianceId: id,
      memberId: 'bob',
      status: 'decline',
    });
    const members = alliances.memberList({ user: alice, allianceId: id });
    assert.equal(members.members?.length, 1);
  });

  it('refuses a request from another country', () => {
    const { alliances, id } = withAlliance();
    const result = alliances.joinRequestSend({ user: carol, targetAllianceId: id }, NOW);
    assert.equal(result.error, ALLIANCE_ERRORS.ERR_WRONG_COUNTRY);
  });

  it('refuses a second request from the same player', () => {
    const { alliances, id } = withAlliance();
    alliances.joinRequestSend({ user: bob, targetAllianceId: id }, NOW);
    const second = alliances.joinRequestSend({ user: bob, targetAllianceId: id }, NOW);
    assert.equal(second.error, ALLIANCE_ERRORS.ERR_JOIN_SEND);
  });

  it('refuses a request to an alliance the player is already in', () => {
    const { alliances, id } = withAlliance();
    const result = alliances.joinRequestSend({ user: alice, targetAllianceId: id }, NOW);
    assert.equal(result.error, ALLIANCE_ERRORS.ERR_MEMBER_BELONGS);
  });

  it('refuses a request to an alliance that does not exist', () => {
    const result = service().joinRequestSend({ user: bob, targetAllianceId: '999' }, NOW);
    assert.equal(result.error, ALLIANCE_ERRORS.ERR_ALLIANCE_NOT_EXISTS);
  });

  it('refuses to process a request that was never made', () => {
    const { alliances, id } = withAlliance();
    const result = alliances.joinRequestProcess({
      user: alice,
      allianceId: id,
      memberId: 'nobody',
      status: 'accept',
    });
    assert.equal(result.error, ALLIANCE_ERRORS.ERR_JOIN_NOT_EXIST);
  });

  it('refuses to list the requests for anyone but the owner', () => {
    const { alliances, id } = withAlliance();
    alliances.joinRequestSend({ user: bob, targetAllianceId: id }, NOW);
    const result = alliances.joinRequestList({ user: bob, allianceId: id });
    assert.equal(result.error, ALLIANCE_ERRORS.ERR_MEMBER_NOT_OWNER);
  });
});

describe('finding an alliance', () => {
  it('finds by title', () => {
    const alliances = service();
    alliances.create({ user: alice, title: 'The Brigade' }, NOW);
    const found = alliances.find({ user: bob, title: 'brigade' });
    assert.equal(found.success, true);
    assert.equal(found.alliances?.length, 1);
  });

  it('does not cross the country line', () => {
    const alliances = service();
    alliances.create({ user: alice, title: 'The Brigade' }, NOW);
    const found = alliances.find({ user: carol, title: 'brigade' });
    assert.equal(found.alliances?.length, 0);
  });

  it('pages the results', () => {
    const alliances = service();
    alliances.create({ user: alice, title: 'First' }, NOW);
    alliances.create({ user: bob, title: 'Second' }, NOW);
    const first = alliances.find({ user: alice, perPage: 1, pageNo: 1 });
    assert.equal(first.alliances?.length, 1);
    const second = alliances.find({ user: alice, perPage: 1, pageNo: 2 });
    assert.equal(second.alliances?.length, 1);
    assert.notEqual(first.alliances?.[0]?.id, second.alliances?.[0]?.id);
  });

  it('lists only the open ones when asked', () => {
    const alliances = new AllianceService([], [alice, bob], { ...DEFAULT_ALLIANCE_RULES, maxMembers: 1 });
    alliances.create({ user: alice, title: 'Full' }, NOW);
    const found = alliances.find({ user: bob, openOnly: true });
    assert.equal(found.alliances?.length, 0);
  });
});

describe('the members', () => {
  function withTwo(): { alliances: AllianceService; id: string } {
    const alliances = service();
    const created = alliances.create({ user: alice, title: 'Brigade' }, NOW);
    alliances.joinRequestSend({ user: bob, targetAllianceId: created.alliance!.id }, NOW);
    alliances.joinRequestProcess({
      user: alice,
      allianceId: created.alliance!.id,
      memberId: 'bob',
      status: 'accept',
    });
    return { alliances, id: created.alliance!.id };
  }

  it('lists them all when asked for -1', () => {
    const { alliances, id } = withTwo();
    const listed = alliances.memberList({ user: alice, allianceId: id, members: -1 });
    assert.equal(listed.members?.length, 2);
  });

  it('lists only the ids when asked', () => {
    const { alliances, id } = withTwo();
    const listed = alliances.memberList({ user: alice, allianceId: id, idsOnly: true });
    assert.equal(listed.members?.length, 2);
    assert.equal(listed.members?.[0]?.bestUnit, undefined);
  });

  it('lets a member leave', () => {
    const { alliances, id } = withTwo();
    const result = alliances.memberLeave({ user: bob });
    assert.equal(result.success, true);
    const listed = alliances.memberList({ user: alice, allianceId: id });
    assert.equal(listed.members?.length, 1);
  });

  it('refuses to let the owner leave', () => {
    const { alliances } = withTwo();
    const result = alliances.memberLeave({ user: alice });
    assert.equal(result.error, ALLIANCE_ERRORS.ERR_ALLIANCE_OWNER_SWITCH);
  });

  it('refuses to let a non-member leave', () => {
    const { alliances } = withTwo();
    const result = alliances.memberLeave({ user: carol });
    assert.equal(result.error, ALLIANCE_ERRORS.ERR_MEMBER_NOT_BELONGS);
  });

  it('lets the owner kick a member', () => {
    const { alliances, id } = withTwo();
    const result = alliances.memberKick({ user: alice, allianceId: id, memberId: 'bob' });
    assert.equal(result.success, true);
    const listed = alliances.memberList({ user: alice, allianceId: id });
    assert.equal(listed.members?.length, 1);
  });

  it('refuses a kick by anyone but the owner', () => {
    const { alliances, id } = withTwo();
    const result = alliances.memberKick({ user: bob, allianceId: id, memberId: 'carol' });
    assert.equal(result.error, ALLIANCE_ERRORS.ERR_MEMBER_NOT_OWNER);
  });

  it('refuses to kick somebody who is not a member', () => {
    const { alliances, id } = withTwo();
    const result = alliances.memberKick({ user: alice, allianceId: id, memberId: 'carol' });
    assert.equal(result.error, ALLIANCE_ERRORS.ERR_MEMBER_NOT_BELONGS);
  });
});

describe('the daily bonus tier', () => {
  it('gives the highest tier the member count qualifies for', () => {
    const rewards = [{ members: 0 }, { members: 5 }, { members: 25 }, { members: 45 }];
    assert.equal(allianceBonusTier(0, rewards), 0);
    assert.equal(allianceBonusTier(4, rewards), 0);
    assert.equal(allianceBonusTier(5, rewards), 1);
    assert.equal(allianceBonusTier(24, rewards), 1);
    assert.equal(allianceBonusTier(25, rewards), 2);
    assert.equal(allianceBonusTier(45, rewards), 3);
    assert.equal(allianceBonusTier(100, rewards), 3);
  });
});
