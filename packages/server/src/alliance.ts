/**
 * The alliance service.
 *
 * The upstream server's `alliance/` route is a catch-all that returns
 * `{}`, so the real contract is the client's own: **11 service variants**
 * with their parameters, and **17 error codes** in four bands
 * (`data/AllianceServiceError.as`).
 *
 * A clone that wants alliances has to implement all 11, and it has to
 * return the **exact** error numbers, because the client switches on them.
 *
 * ## The country rule
 *
 * `ERR_WRONG_COUNTRY` (205) means alliances are **country-scoped**: a
 * player cannot join or be found by an alliance in another country. That
 * matches the `userCountry` parameter on `alliance-find`.
 *
 * ## The owner
 *
 * The owner is a member like any other, with two extra powers: they
 * process join requests, and they kick members. `ERR_MEMBER_NOT_OWNER`
 * (200) is what the other members get for trying.
 */
import type { Random } from '@swl/rules';

/**
 * The error vocabulary.
 *
 * The numbers are the client's own, and the client switches on them, so
 * they must be exactly these.
 */
export const ALLIANCE_ERRORS = {
  // System: 1 to 4.
  ERR_SYS_UNKNOWN: 1,
  ERR_SYS_MISSING_ARGS: 2,
  ERR_SYS_INVALID_ARG: 3,
  ERR_SYS_USER_NOT_EXIST: 4,
  // Alliance: 100 to 103.
  ERR_ALLIANCE_EXISTS: 100,
  ERR_ALLIANCE_NOT_EXISTS: 101,
  ERR_ALLIANCE_CREATE: 102,
  ERR_ALLIANCE_OWNER_SWITCH: 103,
  // Member: 200 to 205.
  ERR_MEMBER_NOT_OWNER: 200,
  ERR_MEMBER_BELONGS: 201,
  ERR_MEMBER_NOT_BELONGS: 202,
  ERR_MEMBER_KICK: 203,
  ERR_MEMBER_LIMIT: 204,
  ERR_WRONG_COUNTRY: 205,
  // Join request: 300 to 302.
  ERR_JOIN_SEND: 300,
  ERR_JOIN_PROCESS: 301,
  ERR_JOIN_NOT_EXIST: 302,
} as const;

export type AllianceErrorCode = (typeof ALLIANCE_ERRORS)[keyof typeof ALLIANCE_ERRORS];

/** A player, as the alliance service sees them. */
export interface AllianceUser {
  id: string;
  name: string;
  /** The player's country code. Alliances do not cross countries. */
  country: string;
  /** The player's best unit, for the alliance's unit list. */
  bestUnit?: number;
}

/** A member of an alliance. */
export interface AllianceMember {
  id: string;
  name: string;
  /** The member's best unit. */
  bestUnit?: number;
  /** Whether the member is logged in. */
  loggedIn?: boolean;
}

/** A request to join. */
export interface JoinRequest {
  memberId: string;
  memberName: string;
  bestUnit?: number;
  /** When the request was made, in seconds. */
  requestedAt: number;
}

/** An alliance. */
export interface Alliance {
  id: string;
  title: string;
  description: string;
  ownerId: string;
  /** The country the alliance belongs to. */
  country: string;
  /** The members, the owner first. */
  members: AllianceMember[];
  /** The requests to join. */
  joinRequests: JoinRequest[];
  /** When the alliance was created, in seconds. */
  dateCreated: number;
  /** The alliance's points, and the XP of its members. */
  totalPoints?: number;
  totalXP?: number;
}

/** The answer to an alliance operation. */
export interface AllianceResult {
  /** Whether the operation succeeded. */
  success: boolean;
  /** The error code, when it failed. */
  error?: number;
  /** The alliance, for the operations that return one. */
  alliance?: Alliance;
  /** The alliances, for the list and find operations. */
  alliances?: Alliance[];
  /** The members, for the member list. */
  members?: AllianceMember[];
  /** The join requests, for the join request list. */
  joinRequests?: JoinRequest[];
}

/** The rules the service applies. */
export interface AllianceRules {
  /** How many members an alliance may have. */
  maxMembers: number;
  /** How many best units an alliance may list. */
  maxBestUnits: number;
  /** How many attacks a member may make a day. */
  maxAttacksADay: number;
  /** The minimum members for the daily bonus. */
  dailyBonusMinMembers: number;
  /** How many join requests may be pending at once. */
  maxJoinRequests?: number;
}

/**
 * The client's own rules.
 *
 * `MAX_BEST_UNITS`, `MAX_ATTACKS_A_DAY` and `DAILY_BONUS_MIN_MEMBERS` are
 * the client's (`data/AllianceInfo.as:33-38`). The **member cap is not
 * a client constant** - the client only knows `slotsLeft`, which the
 * server computes - so it is a rule of this module, and it is documented
 * as such rather than pretended to be the client's.
 */
export const DEFAULT_ALLIANCE_RULES: AllianceRules = {
  maxMembers: 50,
  maxBestUnits: 5,
  maxAttacksADay: 3,
  dailyBonusMinMembers: 2,
  maxJoinRequests: 50,
};

/** The parameters every operation takes. */
export interface AllianceParams {
  /** The player's id. */
  userId?: string;
  /** The player, for the country and the name. */
  user?: AllianceUser;
  /** The alliance's id. */
  allianceId?: string;
  /** The alliance's title. */
  title?: string;
  /** The alliance's description. */
  description?: string;
  /** The player's best unit. */
  bestUnit?: number;
  /** The members to list: -1 for all. */
  members?: number;
  /** The country to search in. */
  userCountry?: string;
  /** Whether only open alliances are returned. */
  openOnly?: boolean;
  /** The page number. */
  pageNo?: number;
  /** How many per page. */
  perPage?: number;
  /** The member being processed, kicked or leaving. */
  memberId?: string;
  /** The join request's status: accepted or declined. */
  status?: 'accept' | 'decline';
  /** Whether only the ids are returned. */
  idsOnly?: boolean;
  /** The id of the alliance to join. */
  targetAllianceId?: string;
}

/**
 * The alliance service.
 *
 * It is **pure**: the state is passed in and the new state is returned,
 * with no clock and no randomness of its own. The clock and the random
 * source are parameters, so a test is deterministic.
 */
export class AllianceService {
  private readonly rules: AllianceRules;
  private alliances: Alliance[] = [];
  private users = new Map<string, AllianceUser>();
  private nextId = 1;

  constructor(
    alliances: readonly Alliance[] = [],
    users: readonly AllianceUser[] = [],
    rules: AllianceRules = DEFAULT_ALLIANCE_RULES,
  ) {
    this.rules = rules;
    this.alliances = alliances.map((alliance) => ({
      ...alliance,
      members: alliance.members.map((member) => ({ ...member })),
      joinRequests: alliance.joinRequests.map((request) => ({ ...request })),
    }));
    for (const user of users) {
      this.users.set(user.id, user);
    }
  }

  /** Register a player. */
  addUser(user: AllianceUser): void {
    this.users.set(user.id, user);
  }

  /** The alliances, for the tests and for the persistence layer. */
  all(): Alliance[] {
    return this.alliances.map((alliance) => ({ ...alliance }));
  }

  /** The failure helper. */
  private fail(code: AllianceErrorCode): AllianceResult {
    return { success: false, error: code };
  }

  /** The player's own record. */
  private userOf(params: AllianceParams): AllianceUser | null {
    if (params.user) return params.user;
    if (!params.userId) return null;
    return this.users.get(params.userId) ?? null;
  }

  /** The alliance with an id. */
  private allianceOf(id: string | undefined): Alliance | null {
    if (!id) return null;
    return this.alliances.find((alliance) => alliance.id === id) ?? null;
  }

  /** `alliance-create` */
  create(params: AllianceParams, now: number): AllianceResult {
    const user = this.userOf(params);
    if (!user) return this.fail(ALLIANCE_ERRORS.ERR_SYS_USER_NOT_EXIST);
    if (!params.title || params.title.trim() === '') {
      return this.fail(ALLIANCE_ERRORS.ERR_SYS_MISSING_ARGS);
    }
    if (
      this.alliances.some(
        (alliance) =>
          alliance.ownerId === user.id &&
          alliance.title.toLowerCase() === params.title!.toLowerCase(),
      )
    ) {
      return this.fail(ALLIANCE_ERRORS.ERR_ALLIANCE_EXISTS);
    }
    const alliance: Alliance = {
      id: String(this.nextId++),
      title: params.title,
      description: params.description ?? '',
      ownerId: user.id,
      country: user.country,
      members: [{ id: user.id, name: user.name, bestUnit: params.bestUnit }],
      joinRequests: [],
      dateCreated: now,
    };
    this.alliances.push(alliance);
    return { success: true, alliance: { ...alliance } };
  }

  /** `alliance-update` */
  update(params: AllianceParams): AllianceResult {
    const user = this.userOf(params);
    if (!user) return this.fail(ALLIANCE_ERRORS.ERR_SYS_USER_NOT_EXIST);
    const alliance = this.allianceOf(params.allianceId);
    if (!alliance) return this.fail(ALLIANCE_ERRORS.ERR_ALLIANCE_NOT_EXISTS);
    if (alliance.ownerId !== user.id) {
      return this.fail(ALLIANCE_ERRORS.ERR_MEMBER_NOT_OWNER);
    }
    if (params.description !== undefined) {
      alliance.description = params.description;
    }
    return { success: true, alliance: { ...alliance } };
  }

  /** `alliance-info` */
  info(params: AllianceParams): AllianceResult {
    const user = this.userOf(params);
    if (!user) return this.fail(ALLIANCE_ERRORS.ERR_SYS_USER_NOT_EXIST);
    const alliance = this.allianceOf(params.allianceId);
    if (!alliance) return this.fail(ALLIANCE_ERRORS.ERR_ALLIANCE_NOT_EXISTS);
    return { success: true, alliance: { ...alliance } };
  }

  /** `alliance-list` — the alliances the player belongs to. */
  list(params: AllianceParams): AllianceResult {
    const user = this.userOf(params);
    if (!user) return this.fail(ALLIANCE_ERRORS.ERR_SYS_USER_NOT_EXIST);
    const mine = this.alliances.filter((alliance) =>
      alliance.members.some((member) => member.id === user.id),
    );
    return { success: true, alliances: mine.map((alliance) => ({ ...alliance })) };
  }

  /** `alliance-find` */
  find(params: AllianceParams): AllianceResult {
    const user = this.userOf(params);
    if (!user) return this.fail(ALLIANCE_ERRORS.ERR_SYS_USER_NOT_EXIST);
    const country = params.userCountry ?? user.country;
    const title = params.title?.toLowerCase();
    const found = this.alliances.filter((alliance) => {
      if (alliance.country !== country) return false;
      if (title && !alliance.title.toLowerCase().includes(title)) return false;
      if (params.openOnly && alliance.members.length >= this.rules.maxMembers) {
        return false;
      }
      return true;
    });
    const pageNo = Math.max(1, params.pageNo ?? 1);
    const perPage = Math.max(1, params.perPage ?? 20);
    const start = (pageNo - 1) * perPage;
    return {
      success: true,
      alliances: found.slice(start, start + perPage).map((alliance) => ({ ...alliance })),
    };
  }

  /** `join-request-send` */
  joinRequestSend(params: AllianceParams, now: number): AllianceResult {
    const user = this.userOf(params);
    if (!user) return this.fail(ALLIANCE_ERRORS.ERR_SYS_USER_NOT_EXIST);
    const alliance = this.allianceOf(params.targetAllianceId ?? params.allianceId);
    if (!alliance) return this.fail(ALLIANCE_ERRORS.ERR_ALLIANCE_NOT_EXISTS);
    if (alliance.country !== user.country) {
      return this.fail(ALLIANCE_ERRORS.ERR_WRONG_COUNTRY);
    }
    if (alliance.members.some((member) => member.id === user.id)) {
      return this.fail(ALLIANCE_ERRORS.ERR_MEMBER_BELONGS);
    }
    if (alliance.joinRequests.some((request) => request.memberId === user.id)) {
      return this.fail(ALLIANCE_ERRORS.ERR_JOIN_SEND);
    }
    if (
      this.rules.maxJoinRequests !== undefined &&
      alliance.joinRequests.length >= this.rules.maxJoinRequests
    ) {
      return this.fail(ALLIANCE_ERRORS.ERR_JOIN_SEND);
    }
    alliance.joinRequests.push({
      memberId: user.id,
      memberName: user.name,
      bestUnit: params.bestUnit,
      requestedAt: now,
    });
    return { success: true };
  }

  /** `join-request-list` */
  joinRequestList(params: AllianceParams): AllianceResult {
    const user = this.userOf(params);
    if (!user) return this.fail(ALLIANCE_ERRORS.ERR_SYS_USER_NOT_EXIST);
    const alliance = this.allianceOf(params.allianceId);
    if (!alliance) return this.fail(ALLIANCE_ERRORS.ERR_ALLIANCE_NOT_EXISTS);
    if (alliance.ownerId !== user.id) {
      return this.fail(ALLIANCE_ERRORS.ERR_MEMBER_NOT_OWNER);
    }
    return {
      success: true,
      joinRequests: alliance.joinRequests.map((request) => ({ ...request })),
    };
  }

  /** `join-request-process` */
  joinRequestProcess(params: AllianceParams): AllianceResult {
    const user = this.userOf(params);
    if (!user) return this.fail(ALLIANCE_ERRORS.ERR_SYS_USER_NOT_EXIST);
    const alliance = this.allianceOf(params.allianceId);
    if (!alliance) return this.fail(ALLIANCE_ERRORS.ERR_ALLIANCE_NOT_EXISTS);
    if (alliance.ownerId !== user.id) {
      return this.fail(ALLIANCE_ERRORS.ERR_MEMBER_NOT_OWNER);
    }
    const index = alliance.joinRequests.findIndex(
      (request) => request.memberId === params.memberId,
    );
    if (index < 0) return this.fail(ALLIANCE_ERRORS.ERR_JOIN_NOT_EXIST);

    const request = alliance.joinRequests[index]!;
    alliance.joinRequests.splice(index, 1);

    if (params.status === 'accept') {
      if (alliance.members.length >= this.rules.maxMembers) {
        return this.fail(ALLIANCE_ERRORS.ERR_MEMBER_LIMIT);
      }
      const member = this.users.get(request.memberId);
      if (member && member.country !== alliance.country) {
        return this.fail(ALLIANCE_ERRORS.ERR_WRONG_COUNTRY);
      }
      alliance.members.push({
        id: request.memberId,
        name: request.memberName,
        bestUnit: request.bestUnit,
      });
    }
    return { success: true };
  }

  /** `member-list` */
  memberList(params: AllianceParams): AllianceResult {
    const user = this.userOf(params);
    if (!user) return this.fail(ALLIANCE_ERRORS.ERR_SYS_USER_NOT_EXIST);
    const alliance = this.allianceOf(params.allianceId);
    if (!alliance) return this.fail(ALLIANCE_ERRORS.ERR_ALLIANCE_NOT_EXISTS);

    // -1 means every member.
    const limit = params.members === undefined || params.members < 0
      ? alliance.members.length
      : Math.min(params.members, alliance.members.length);
    const members = alliance.members.slice(0, limit).map((member) => ({ ...member }));
    return {
      success: true,
      members: params.idsOnly ? members.map((member) => ({ id: member.id, name: member.name })) : members,
    };
  }

  /** `member-leave` */
  memberLeave(params: AllianceParams): AllianceResult {
    const user = this.userOf(params);
    if (!user) return this.fail(ALLIANCE_ERRORS.ERR_SYS_USER_NOT_EXIST);
    const alliance = this.alliances.find((candidate) =>
      candidate.members.some((member) => member.id === user.id),
    );
    if (!alliance) return this.fail(ALLIANCE_ERRORS.ERR_MEMBER_NOT_BELONGS);
    if (alliance.ownerId === user.id) {
      // The owner cannot just walk away: the alliance would be left with
      // nobody who can process its join requests.
      return this.fail(ALLIANCE_ERRORS.ERR_ALLIANCE_OWNER_SWITCH);
    }
    alliance.members = alliance.members.filter((member) => member.id !== user.id);
    return { success: true };
  }

  /** `member-kick` */
  memberKick(params: AllianceParams): AllianceResult {
    const user = this.userOf(params);
    if (!user) return this.fail(ALLIANCE_ERRORS.ERR_SYS_USER_NOT_EXIST);
    const alliance = this.allianceOf(params.allianceId);
    if (!alliance) return this.fail(ALLIANCE_ERRORS.ERR_ALLIANCE_NOT_EXISTS);
    if (alliance.ownerId !== user.id) {
      return this.fail(ALLIANCE_ERRORS.ERR_MEMBER_NOT_OWNER);
    }
    if (!params.memberId) return this.fail(ALLIANCE_ERRORS.ERR_SYS_MISSING_ARGS);
    if (!alliance.members.some((member) => member.id === params.memberId)) {
      return this.fail(ALLIANCE_ERRORS.ERR_MEMBER_NOT_BELONGS);
    }
    if (params.memberId === alliance.ownerId) {
      // The owner cannot be kicked by themselves.
      return this.fail(ALLIANCE_ERRORS.ERR_ALLIANCE_OWNER_SWITCH);
    }
    alliance.members = alliance.members.filter((member) => member.id !== params.memberId);
    return { success: true };
  }
}

/**
 * The daily bonus tier a member count qualifies for.
 *
 * The tiers are the content's `ALLIANCE_DAILY_BONUS_REWARDS`: 0, 5, 25
 * and 45 members, and the player gets the **highest** tier they qualify
 * for.
 */
export function allianceBonusTier(
  members: number,
  rewards: readonly { members: number }[],
): number {
  let tier = -1;
  for (let index = 0; index < rewards.length; index++) {
    if (members >= rewards[index]!.members) tier = index;
  }
  return tier;
}
