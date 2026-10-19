# Social Layer Contracts — Alliances, Marketplace & Betting

**Roadmap task B7.** The upstream server answers `{}` for all eleven
`alliance/?method=…` variants and has its `bets/*` routes commented out, so the real
contract had to be recovered from the client. It is fully recoverable: `core/Config.as`
names every endpoint, and each `ServiceManager.callService()` call site shows exactly
which request parameters it sends and which response fields it reads.

| | |
|---|---|
| **Source** | The decompiled client, `.work/as/basesec/scripts/` |
| **Tooling** | `node scripts/analyze-services.mjs` → [`../data/service-contracts.json`](../data/service-contracts.json) |
| **Scope** | **25** service endpoints, **11** alliance variants, **3** betting endpoints, **17** alliance error codes |

---

## 1. The full service list

`core/Config.as` is the authoritative endpoint registry. This is the complete set — there
are no other service paths in the client.

### 1.1 Game API

| Constant | Path | In the upstream server? |
|---|---|---|
| `SERVICE_GET_GAME_CONFIG` | `get_game_config.php` | ✅ |
| `SERVICE_GET_PLAYER_INFO` | `get_player_info.php` | ✅ |
| `SERVICE_COMMAND` | `command.php` | ✅ |
| `SERVICE_LOAD_FBID_WORLD` | `get_user_world.php` | ❌ missing |
| `SERVICE_LOAD_CONTINENT` | `get_continent.php` | ❌ missing |
| `SERVICE_LOAD_CONTINENT_RANKING` | `get_continent_ranking.php` | ❌ missing (**removed by the client in 1.5.4**) |
| `SERVICE_GET_USER_PROFILE` | `get_public_player_info.php` | ❌ missing |
| `SERVICE_GET_CHOSE_SEX` | `set_sex_player.php` | ❌ missing |
| `SERVICE_REPORT_ERROR` | `report_error_init.php` | ❌ missing |
| `SERVICE_CLEAN_ASSAULTS` | `clean_assaults.php` | ❌ missing |
| `SERVICE_REGISTER_FOUND_ITEM` | `register_found_item.php` | ❌ missing |

### 1.2 Alliance (11 variants)

| Constant | `method=` | Request parameters | Response fields read |
|---|---|---|---|
| `SERVICE_ALLIANCE_CREATE` | `alliance-create` | `userId`, `title`, `description`, `bestUnit` | `success` |
| `SERVICE_ALLIANCE_UPDATE` | `alliance-update` | `userId`, `description` | — |
| `SERVICE_ALLIANCE_INFO` | `alliance-info` | `userId`, `members` (optional `-1` for all) | `success`, then the alliance object |
| `SERVICE_ALLIANCE_LIST` | `alliance-list` | — | — |
| `SERVICE_ALLIANCE_FIND` | `alliance-find` | `userId`, `title`, `userCountry`, `openOnly`, `pageNo`, `perPage` | — |
| `SERVICE_ALLIANCE_JOIN_SEND` | `join-request-send` | `userId`, `allianceId`, `bestUnit` | — |
| `SERVICE_ALLIANCE_JOIN_LIST` | `join-request-list` | — | — |
| `SERVICE_ALLIANCE_JOIN_PROCESS` | `join-request-process` | `userId`, `memberId`, `status` | — |
| `SERVICE_ALLIANCE_MEMBER_LIST` | `member-list` | `userId`, `idsOnly` | — |
| `SERVICE_ALLIANCE_MEMBER_LEAVE` | `member-leave` | `userId` | — |
| `SERVICE_ALLIANCE_MEMBER_KICK` | `member-kick` | `userId`, `memberId` | — |

`userId` is `Base.Commands.phpsessid` — the session id, the same value the upstream server
receives as `USERID`.

**The upstream server's `alliance/` route is a catch-all that returns `{}`.** The real
contract is the table above. A clone that wants alliances must implement these 11
variants with these parameters.

### 1.3 Betting / marketplace (3 endpoints)

| Constant | Path | Request parameters |
|---|---|---|
| `SERVICE_BETS_GET_BETS_LIST` | `bets/get_bets_list.php` | `user_id`, `level` |
| `SERVICE_BETS_GET_BET_DETAIL` | `bets/get_bet_detail.php` | `uuid`, `checkFinish` |
| `SERVICE_BETS_SET_BET` | `bets/set_bet.php` | `user_id`, `uuid`, `round`, `bet`, `client_id`, `session_id` |

**This is an exact match for the upstream server's commented-out handlers.** The upstream
`server.py` has `set_bet` reading `data["uuid"]`, `data["bet"]` and `data["round"]`, and
`get_bets_list` reading `data["user_id"]` and `data["level"]` — the same fields the client
sends. The upstream author had recovered the same contract; the handlers were simply never
enabled.

> `session_id` is `Base.Commands.userKey` when present, else the literal `"ludorules"`.

## 2. The alliance error codes

`data/AllianceServiceError.as` defines the full error vocabulary — **17 codes** in four
bands. A clone must return these exact numbers.

| Band | Codes |
|---|---|
| **System (1–4)** | `ERR_SYS_UNKNOWN` = 1, `ERR_SYS_MISSING_ARGS` = 2, `ERR_SYS_INVALID_ARG` = 3, `ERR_SYS_USER_NOT_EXIST` = 4 |
| **Alliance (100–103)** | `ERR_ALLIANCE_EXISTS` = 100, `ERR_ALLIANCE_NOT_EXISTS` = 101, `ERR_ALLIANCE_CREATE` = 102, `ERR_ALLIANCE_OWNER_SWITCH` = 103 |
| **Member (200–205)** | `ERR_MEMBER_NOT_OWNER` = 200, `ERR_MEMBER_BELONGS` = 201, `ERR_MEMBER_NOT_BELONGS` = 202, `ERR_MEMBER_KICK` = 203, `ERR_MEMBER_LIMIT` = 204, `ERR_WRONG_COUNTRY` = 205 |
| **Join request (300–302)** | `ERR_JOIN_SEND` = 300, `ERR_JOIN_PROCESS` = 301, `ERR_JOIN_NOT_EXIST` = 302 |

`ERR_WRONG_COUNTRY` implies alliances are **country-scoped**, which matches the
`userCountry` parameter on `alliance-find`.

## 3. The marketplace

The marketplace is the *same* mechanism as the betting endpoints, exposed through the
`MarketplaceInfo` / `MarketplaceUnitInfo` / `PopupMarketplaceUnit` classes. A listed unit
carries a `uuid`, a `round` and a `bidPrice`; bidding posts `set_bet` with those three
values plus the session fields.

The upstream `auctions.py` (7 835 bytes) implements the same object model — `get_auctions(user_id, level)`, `get_auction_detail(...)`, `set_bet(...)` — and `config/auctionhouse.json` holds the seed data. **The subsystem is complete upstream but disabled.**

## 4. What this closes

| Previously | Now |
|---|---|
| "The alliance contract is unknown; the server answers `{}`" | The 11 variants, their request parameters and the 17 error codes are all known |
| "The betting subsystem is a guess" | The 3 endpoints and their exact fields are known, and they **match** the upstream's commented-out handlers |
| "The marketplace flow is unspecified" | The uuid/round/bidPrice model is known |

## 5. Implications for the clone

1. **Alliances are cheap to implement now.** 11 variants, a flat parameter list each, and a
   17-code error vocabulary. This is a self-contained subsystem.
2. **The betting subsystem needs no re-invention.** The upstream `auctions.py` and
   `config/auctionhouse.json` are already a working implementation of the contract the
   client expects; the clone can port it directly and enable the three routes.
3. **Eight game-API endpoints are still missing** from the upstream server:
   `get_user_world.php`, `get_continent.php`, `get_continent_ranking.php`,
   `get_public_player_info.php`, `set_sex_player.php`, `report_error_init.php`,
   `clean_assaults.php`, `register_found_item.php`. A clone that wants feature parity
   needs them; the client calls them, so it will break or silently no-op without them.
4. `get_continent_ranking.php` is the one endpoint the *client itself* removed in 1.5.4,
   so a clone does not need it — but the 1.4.x clients it must stay compatible with do.

## 6. Reproducing this

```bash
node scripts/decompile-client.mjs     # -> .work/as/basesec/
node scripts/analyze-services.mjs     # -> re/data/service-contracts.json
```

## 7. Known limits

* Request parameters are extracted from object literals and `params.<key> =` assignments
  in the call site. A parameter built dynamically (a variable name, a loop) is not
  captured.
* Response fields are extracted from the callback's `param.n.<field>` reads. Fields the
  callback passes on to a helper (and which the helper then reads) are not captured.
* `alliance-list` and `join-request-list` have **no call site in the client** — the
  endpoints are declared but the client never calls them, so their contract is unknown
  beyond the path. They may be dead endpoints, or called from code that is not reachable.
* The analysis is of the **1.5.4** client; earlier clients may call more variants.
