<!--
  Generated investigation artifact.
  Source of truth for the details inside is the file it was produced from:
  decompiled ActionScript 3 (FFDec 26.3.0) of assets/flash/Basesec_1.5.4.swf,
  the Python server sources, and live traffic captured from a real Adobe Flash
  Player session against the local server.
-->

# Network & Protocol Layer

> **Scope:** Static decompilation of the AS3 client (1 387 classes) plus live capture from a real Adobe Flash Player session against the local server.
>
> **Method:** Static decompilation of the AS3 client (1 387 classes) plus live capture from a real Adobe Flash Player session against the local server.
>
> **Subject:** client-side networking: endpoints, flashvars, command.php framing, HMAC signing, map flavours
>
> Part of the Social Wars reverse-engineering report set. See [`../README.md`](../README.md)
> for the document map and [`../docs/00-EXECUTIVE-SUMMARY.md`](00-EXECUTIVE-SUMMARY.md) for the
> cross-cutting conclusions.

---

# Social Wars (Basesec / Social Empires "Basesec_1.5.4") — Network / Protocol Layer

Reverse-engineered from the FFDec-decompiled ActionScript 3 sources under
`<as3-root>\scripts\`.

All `file:line` citations are relative to that `scripts\` root unless stated otherwise.
Line numbers refer to the decompiled output — FFDec output is occasionally imperfect, so
every non-trivial claim below was cross-checked against at least one second call site.

**Legend:** `VERIFIED` = read directly from the decompiled code (or empirically confirmed
against the local preservation server / captured server payloads).
`UNVERIFIED` = inferred, stated as a hypothesis, or dependent on Flash Player internals
that cannot be observed from the decompiled client.

---

## 0. Executive summary of the protocol

| Aspect | Value |
|---|---|
| Transport | HTTP/1.1, `POST` for everything except three `GET` endpoints |
| Root URLs | *dynamic* root from flashvar `dynamicUrl`; *static* root from flashvar `staticUrl` |
| Session id | `USERID` query parameter, value = flashvar `fb_sig_user` (the "php session id") |
| Secondary auth | `user_key` query parameter (flashvar `user_key`) + `accessToken` inside the command body |
| Body envelope | `data=<64 hex chars>;<JSON>` — HMAC-SHA256 hex digest, `;` separator, then raw JSON |
| Command body | JSON object `{first_number, commands, tries, publishActions, ts, flashVersion, accessToken}` |
| Command tuple | `[map_id, cmd, args[], resources_changed[8]]` |
| Server key | `Config.SERVER_KEY = "4vVSD8dftv6hdfb1Hnk9"` (`core/Config.as:72`) |
| Response envelope | Either raw JSON, or `<64 hex>;<JSON>`; the client strips the prefix if present |

---

## 1. Complete HTTP endpoint inventory

### 1.1 Root / base URL construction

**Dynamic (API) root** — `managers/CommandManager.as:120-143` (`Init1`):

```
Init1():
  commandBase = Config.SERVICE_COMMAND                       // "command.php"
  if (serverEnabled) { baseURL = serverUrl; prefix = "swf/"; }
  else              { baseURL = "game/";     prefix = "swf/"; }
  if (!phpsessid) showErrorSync(ERROR_UNKNOWN)
  sessionID = phpsessid
```

`serverUrl` comes **only** from the flashvar `dynamicUrl` (`core/Base.as:1124-1128`).
If that flashvar is absent the game does not start (`canStart` stays `false`,
`core/Base.as:1127` + `core/Base.as:1273-1298`); pressing `Constants.KEY_INTRO`
(`"intro"`) or `Constants.KEY_CONTROL` forces it to fall back to the hardcoded
production URLs (`core/Base.as:2821-2829`, `core/Base.as:2841-2850`):

| Constant | Value | Source |
|---|---|---|
| `Config.URL_SERVER_DVP` | `http://int-sw.socialpointgames.com/sw1/web/srvsexwars/` | `core/Config.as:16` |
| `Config.URL_SERVER_PROD` | `http://dynamicmw.socialpointgames.com/appsfb/menvswomen/srvsexwars/` | `core/Config.as:18` |
| `Config.URL_SERVER` | `""` (empty) | `core/Config.as:14` |

Note the production root contains the literal app id `menvswomen` — this is the same
segment the preservation server reproduces as `/dynamic/menvswomen/srvsexwars`
(`<upstream-repo>\server.py:61`).

**Static (asset) root** — flashvar `staticUrl` → `Base.Main.apfx` (`core/Base.as:865-868`).
Used for sprites, thumbnails, sounds, fonts, images, magic FX (see §1.4).

### 1.2 URL assembly — `getURLWithUserID`

`managers/CommandManager.as:576-603`:

```as3
public function getURLWithUserID(param1:String = null, param2:String = null) : String
{
   if (param1 == null) param1 = this.commandBase;
   _loc3_ = this.baseURL + param1;
   if (this.serverEnabled && param2 == null)      _loc3_ += "?USERID="   + this.sessionID;
   else if (this.serverEnabled && param2 != null) _loc3_ += "?USERID="   + param2;
   if (this.userKey != "")                        _loc3_ += "&user_key=" + this.userKey;
   if (this.debug)                                _loc3_ += "&" + this.weirdSecurity + "=1";
   _loc3_ += "&language=" + Base.Main.localization;
   return _loc3_;
}
```

So **every** dynamic request carries, in the query string:

| Param | Source | Meaning |
|---|---|---|
| `USERID` | flashvar `fb_sig_user` → `CommandManager.phpsessid` → `sessionID` | session / player id. `getURLWithUserID(service, uid)` overrides it with the *target* uid (used by `get_public_player_info.php`). |
| `user_key` | flashvar `user_key` → `CommandManager.userKey` | secondary anti-theft token; omitted entirely when empty. |
| `language` | flashvar `language` (lower-cased) → `Base.Main.localization` | UI language, `en`/`es`/`br`/`it`/`fr`/`de`/`kl`/`tr`/`el` (`core/Language.as:19-35`). |
| `ownueg=1` | debug flag | Only appended when `CommandManager.debug == true`; the parameter *name* is dynamic (see §10.3). |

`getURLRequestWithUserID` (`managers/CommandManager.as:605-629`) is the same idea but
returns a `URLRequest` whose `.data` is a `URLVariables` object with the same keys
(`USERID`, `user_key`, and the debug key) — used by the three `GET` endpoints.

### 1.3 Dynamic (API) endpoints

| # | Path (relative to `dynamicUrl`) | Method | Called from | Notes |
|---|---|---|---|---|
| 1 | `get_game_config.php` | POST (no body) | `core/Base.as:1337` | Static game data. |
| 2 | `get_player_info.php` | POST | `core/Base.as:1416` (own map), `core/Base.as:6990` (neighbour/quest/assault map) | |
| 3 | `set_sex_player.php` | POST | `core/Base.as:1317`, `core/Base.as:1326` | Gender selection on first login. |
| 4 | `command.php` | POST | `managers/CommandManager.as:386-404` | The main command channel. |
| 5 | `sync_error_track.php` | POST | `managers/CommandManager.as:529` | Telemetry when a sync error occurs. |
| 6 | `track_game_status.php` | POST | `core/Base.as:7967` | Funnel/progression telemetry. |
| 7 | `report_error_init.php` | POST | `core/Base.as:1671,1680,1688` | Client-side error reporting (only sent when `Capabilities.isDebugger`). |
| 8 | `get_public_player_info.php` | **GET** | `popups/PopupPlayerProfile.as:84-88` | Public profile of another player. |
| 9 | `get_user_world.php` | **GET** | `popups/PopupAttackFinished.as:543-546` | Resolve a FB uid → world id. |
| 10 | `get_continent_ranking.php` | **GET** | `newTowns/ExplorationsManager.as:286-297` | "Continents"/islands ranking screen. |
| 11 | `alliance/?method=alliance-create` | POST | `popups/alliances/PopupCreateAlliance.as:174` | Alliance service, method in the query string. |
| 12 | `alliance/?method=alliance-update` | POST | `popups/alliances/PopupCreateAlliance.as:167` | |
| 13 | `alliance/?method=alliance-info` | POST | `data/AllianceInfo.as:128` | |
| 14 | `alliance/?method=alliance-list` | POST | `popups/alliances/AllianceState.as:489` | |
| 15 | `alliance/?method=alliance-find` | POST | `popups/alliances/JoinState.as:189` | |
| 16 | `alliance/?method=join-request-send` | POST | `popups/alliances/AllianceInfoRendererItem.as:28` | |
| 17 | `alliance/?method=join-request-list` | POST | `popups/alliances/AllianceState.as:486` | |
| 18 | `alliance/?method=join-request-process` | POST | `popups/alliances/AllianceState.as:159,170` | |
| 19 | `alliance/?method=member-list` | POST | `popups/alliances/AllianceState.as:479`, `popups/alliances/PopupSendAllianceMessage.as:78` | |
| 20 | `alliance/?method=member-leave` | POST | `popups/alliances/AllianceState.as:307` | |
| 21 | `alliance/?method=member-kick` | POST | `popups/alliances/AllianceState.as:179` | |
| 22 | `bets/get_bets_list.php` | POST | `data/MarketplaceInfo.as:92`, `data/MarketplaceUnitInfo.as:129` | Auction house / "marketplace". |
| 23 | `bets/get_bet_detail.php` | POST | `data/MarketplaceUnitInfo.as:137`, `popups/marketplace/PopupMarketplaceUnit.as:463` | |
| 24 | `bets/set_bet.php` | POST | `popups/marketplace/PopupMarketplaceUnit.as:346` | |

Declared-but-unused constants in `core/Config.as` (present in the binary, never
referenced anywhere else — dead code, but they reveal the original API surface):

| Constant | Value | Source |
|---|---|---|
| `SERVICE_REGISTER_FOUND_ITEM` | `register_found_item.php` | `core/Config.as:24` |
| `SERVICE_LOAD_CONTINENT` | `get_continent.php` | `core/Config.as:26` |
| `SERVICE_CLEAN_ASSAULTS` | `clean_assaults.php` | `core/Config.as:34` |

### 1.4 Static (asset) endpoints

All prefixed with `Base.Main.apfx` (flashvar `staticUrl`):

| Pattern | Consumer |
|---|---|
| `apfx + "sprites/" + <img_name> + ".swf"` | `core/Base.as:7303`, `GUI/AnimatedUnit.as:70`, `GUI/AnimatedUnitCentered.as:66`, `popups/PopupRecruitment.as:163` |
| `apfx + "thumbs/" + <img_name> + ".jpg"` | `utils/ThumbManager.as:56`, `GUI/PortraitTrainQueue.as:59`, `popups/PopupSuperMistery.as:154` |
| `apfx + "sounds/" + <file> + ".mp3"` | `core/SoundFile.as:55` |
| `apfx + MUSIC[<bgmId>]` | `managers/SoundManager.as:819,838` |
| `apfx + "fonts/" + [<lang>_]<name> + ".swf"` | `utils/FontsLoader.as:60` (dir set at `core/Base.as:1200`) |
| `apfx + "magic/" + <name> + ".swf"` | `core/magic/MagicSpell.as:92` |
| `apfx + "fx/" + <name> + ".swf"` | `managers/ProjectileManager.as:141` |
| `apfx + "characters_2/" + <file>` | `cutscene/Character.as:77` (`Config.CHARACTERS_FOLDER`, `core/Config.as:242`) |
| `apfx + "images/" + [<lang>/]<file>` | `core/ImageLoader.as:47` (language folder resolved from `Base.Items.localizationImgs`) |
| `apfx + "images/flags/" + <country>.png` | `popups/alliances/PopupAlliancesCenter.as:39` |
| `apfx + "bigbosses/bigboss1.jpg"` | `core/Base.as:1206` |
| `apfx + <url>` (generic, queued loader) | `core/AssetLoader.as:84` |

Non-`apfx` URLs:

| URL | Purpose | Source |
|---|---|---|
| `https://graph.facebook.com/<uid>/picture?type=<square>` | FB avatar | `core/GameStatic.as:427` (via `utils/SecureImageLoader.as:36`) |
| `../locale/<getText>` or `<getText>` | gettext MO catalogue | `core/Language.as:61-66`, `utils/gettext/GetText.as:245-265` |
| `externalized/weird.txt` | debug-token discovery (relative) | `core/Base.as:1112` |
| `http://dynamic.flash1.dev.socialpoint.es/appsfb/socialwarsdev/locale/` | dev locale fallback (only when flashvar `getText` is absent) | `core/Language.as:61` |

---

## 2. Request parameters per endpoint

### 2.1 `get_game_config.php`

* **Method:** POST. **Body:** none (`getInfo(..., null, ...)` → `managers/CommandManager.as:233-251`).
* **Query:** `USERID`, `user_key`, `language` (+ optional debug key).

### 2.2 `get_player_info.php`

* **Method:** POST. **Query:** `USERID`, `user_key`, `language`.
* **Body** (`URLVariables`):

| Param | Type | Meaning | Source |
|---|---|---|---|
| `neighbors` | comma-joined String | list of friend uids (`fb_sig_friends` split on `,`) | `core/Base.as:1408`, `core/Base.as:5149-5161` |
| `client_id` | Number | random per-session id, `Math.round(Math.random()*1073741824)` | `core/Base.as:887`, `core/Base.as:1409` |
| `user` | String | **only** for neighbour/quest/assault maps: the target uid | `core/Base.as:6974-6977` |
| `map` | String | **only** when a specific map of the target is requested (0-based) | `core/Base.as:6978-6981` |
| `privateState` | `1` | **only** in ASSAULT mode and *not* in quest mode | `core/Base.as:6982-6987` |

The own-map call sends only `neighbors` + `client_id`; the "visit someone else" call
sends `user` (+`map`, +`privateState`).

### 2.3 `set_sex_player.php`

* **Method:** POST. **Query:** `USERID`, `user_key`, `language`.
* **Body:** `race` = `"m"` (male) or `"w"` (female) — `core/Base.as:1315`, `core/Base.as:1323`,
  values from `core/Constants.as:1758` (`GENDER_FEMALE="w"`) and `core/Constants.as:1760` (`GENDER_MALE="m"`).
  The female branch additionally sends `user_id` = `phpsessid` (`core/Base.as:1324`).
  (The asymmetric `user_id` looks like a bug in the original client — it is present in the SWF.)

### 2.4 `command.php`

* **Method:** POST (`managers/CommandManager.as:400`).
* **Query:** `USERID`, `user_key`, `language`.
* **Body** (form-encoded, `URLVariables`, `managers/CommandManager.as:388-399`):

| Field | Type | Value |
|---|---|---|
| `data` | String | `"<64-hex-hash>;<json-body>"` — see §4 and §6 |
| `client_id` | Number | `Base.Main.clientId` (`managers/CommandManager.as:398`) |

The JSON body of `data` is:

```json
{
  "first_number":  <Number>,
  "commands":      [ [map_id, cmd, args, resources_changed], ... ],
  "tries":         <Number>,
  "publishActions": "0" | "1",
  "ts":            <Number>,       // server-synchronised epoch seconds
  "flashVersion":  "1.5.4",
  "accessToken":   <String>
}
```

(exact literal at `managers/CommandManager.as:389-397`).

### 2.5 `sync_error_track.php`

* **Method:** POST (`managers/CommandManager.as:531`). **Query:** `USERID`, `user_key`, `language`.
* **Body** (`managers/CommandManager.as:505-528`):

| Param | Type | Meaning |
|---|---|---|
| `user_id` | String | `phpsessid` |
| `command_number` | Number | `currentPacket.firstNumber` (only if a packet is in flight) |
| `tries` | Number | `currentPacket.tries` (only if a packet is in flight) |
| `previous_failed` | `"0"`/`"1"` | whether the previous packet failed |
| `current_failed` | `"0"`/`"1"` | whether the current packet failed |
| `error` | String | one of the `ERROR_*` codes (§5.4) |
| `description` | String | free-text server description |
| `game_mode` | Number | `Base.Main.gameMode` (0 tutorial, 1 normal, 2 neighbour, 3 assault, 4 campaign, 10 editor — `core/Constants.as:1826-1836`) |
| `spy` | Boolean | only in `GAME_MODE_ASSAULT` |
| `quest` | Boolean | only in `GAME_MODE_ASSAULT` |
| *(extra)* | any | `showErrorSync(..., param3)` merges an arbitrary object of extra fields |

### 2.6 `track_game_status.php`

* **Method:** POST (`core/Base.as:7974`). **URL:** `dynamicUrl` + `track_game_status.php`,
  falling back to `Config.URL_SERVER_DVP` when the `dynamicUrl` flashvar is absent
  (`core/Base.as:7950-7954`).
* **Body** (`core/Base.as:7968-7971`): `user_id` (String, `fb_sig_user`),
  `status` (String), `installId` (String, flashvar `install_id`, default `"0"`).
* `status` is a **monotonic funnel token**, compared lexicographically by
  `statusGreaterThan()` (`core/Base.as:7914-7926`); the previous status arrives as the
  flashvar `game_status` (`core/Base.as:7942-7945`). Observed values:
  `000-construct`, `090-endconstruct`, `091-fontsloaded`, `100-config`, `110-pinfo`,
  `120-init`, `3<LLL>-lev` (level-up, `core/Base.as:461-464`).

### 2.7 `report_error_init.php`

* **Method:** POST via `ServiceManager.callService` (default `param5=true` → body is hash-framed).
* **Body JSON:** `user_id` (String), `message` (String), `stacktrace` (String)
  — `core/Base.as:1671-1693`.

### 2.8 `get_public_player_info.php` (GET)

* **Method:** GET (`popups/PopupPlayerProfile.as:87`).
* **Query:** `USERID` = **the target player's uid** (2nd arg of `getURLWithUserID`,
  `popups/PopupPlayerProfile.as:84`), plus `user_key`, `language`.
* **Body:** none.

### 2.9 `get_user_world.php` (GET)

* **Method:** GET (`popups/PopupAttackFinished.as:546`).
* **Query:** `USERID`, `user_key`, `language` (from `getURLRequestWithUserID`).
* **Body (as URLVariables on a GET request — Flash appends them to the query string):**
  `user_id` (String), `map` (int) — `popups/PopupAttackFinished.as:544-545`.

### 2.10 `get_continent_ranking.php` (GET)

* **Method:** GET (`newTowns/ExplorationsManager.as:297`).
* **Query:** `USERID`, `user_key`, `language`.
* **Body/extra query params:** `map` (= `Base.Main.townID`), `worldChange`
  (= `Base.Player.privateState.worldChange`), `relocate` = `"1"` (optional),
  `level_id` (optional) — `newTowns/ExplorationsManager.as:287-296`.

### 2.11 Alliance service (`alliance/?method=<m>`)

All POST via `ServiceManager.callService` → body is `<hash>;<json>` with the JSON
encoded from a plain object.

| `method` | JSON body fields | Source |
|---|---|---|
| `alliance-create` | `userId`, `title`, `description`, `bestUnit` | `popups/alliances/PopupCreateAlliance.as:174-179` |
| `alliance-update` | `userId`, `description` | `popups/alliances/PopupCreateAlliance.as:167-170` |
| `alliance-info` | `userId`, `members` = `-1` (when the full member list is wanted) | `data/AllianceInfo.as:123-127` |
| `alliance-list` | `userId`, `perPage`, `pageNo` (unless ranked), `title` (search) | `popups/alliances/AllianceState.as:468-494` |
| `alliance-find` | `userId`, `pageNo`, `title`, `perPage`, `openOnly`, `userCountry` | `popups/alliances/JoinState.as:189-196` |
| `join-request-send` | `userId`, `allianceId`, `bestUnit` | `popups/alliances/AllianceInfoRendererItem.as:28-32` |
| `join-request-list` | `userId`, `perPage`, `pageNo` | `popups/alliances/AllianceState.as:486,495` |
| `join-request-process` | `userId`, `memberId`, `status` = `"accept"` \| `"reject"` | `popups/alliances/AllianceState.as:159-174` |
| `member-list` | `userId`, `perPage`, `pageNo`, `title` (search), `idsOnly` = `1` | `popups/alliances/AllianceState.as:479-483`, `popups/alliances/PopupSendAllianceMessage.as:78-81` |
| `member-leave` | `userId` | `popups/alliances/AllianceState.as:307` |
| `member-kick` | `userId`, `memberId` | `popups/alliances/AllianceState.as:179-182` |

`userId` is always the player's own `phpsessid`; `bestUnit` is
`AllianceInfo.userBestUnitId` (default `Constants.ID_UNIT_WORKER_1`,
`core/Base.as:1606-1613`); `userCountry` is `Base.Player.country`
(flashvar `userCountry`, default `"us"`, `managers/PlayerStatus.as:304-305`).

### 2.12 Auction house / marketplace (`bets/*.php`)

| Endpoint | JSON body | Source |
|---|---|---|
| `bets/get_bets_list.php` | `user_id`, `level` | `data/MarketplaceInfo.as:92-95`, `data/MarketplaceUnitInfo.as:129-132` |
| `bets/get_bet_detail.php` | `uuid` (+ optional `checkFinish` = `1`) | `data/MarketplaceUnitInfo.as:137-140`, `popups/marketplace/PopupMarketplaceUnit.as:463` |
| `bets/set_bet.php` | `user_id`, `uuid`, `round`, `bet`, `client_id` (String), `session_id` (`user_key` or `"ludorules"`) | `popups/marketplace/PopupMarketplaceUnit.as:335-342` |

---

## 3. Response payload shapes as parsed by the client

### 3.1 Generic response unwrapping

Two different unwrap paths exist.

**(a) `ServiceManager` (used by alliance + bets):** `managers/ServiceManager.as:76-96`

```as3
var _loc3_:Object = Crypto.getHashAndPayload(_loc2_.data);   // strips "<hash>;" if present
var _loc5_:Object = JSON.decode(_loc3_["payload"]);
if (_loc5_.hasOwnProperty("success")) handler(_loc5_);        // whole object
else                                      handler(_loc5_["data"]);  // the "data" sub-object
```

So a service response is either

```json
{ "success": 1, ...extra fields consumed directly by the handler... }
```

or

```json
{ "result": "success", "data": { ...fields the handler consumes... } }
```

Both work. The alliance handlers test `param1.success` truthiness
(`data/AllianceInfo.as:130`, `popups/alliances/AllianceState.as:517`).
The bets-list handler reads `param1.bets` (`data/MarketplaceInfo.as:118-121`), i.e. in
the `{"result":"success","data":{"bets":[...]}}` form the handler receives the `data`
object which contains `bets`. The preservation server's commented-out implementation
uses exactly that shape (`server.py:218-226`).

**(b) `CommandManager.getInfo` (used by config/player-info/sex):** the raw response body
is handed to the callback unchanged; the callback then does its own
`Crypto.getHashAndPayload()` + `JSON.decode()`.

### 3.2 `get_game_config.php`

Top-level object (as consumed by `managers/GameDataManager.as:120-180`):

| Key | Consumer | Notes |
|---|---|---|
| `globals` | `GameDataManager.globals` | Object; `globals.DEPOT_LIMITS` is a **JSON string** that is `JSON.decode`d again (`managers/GameDataManager.as:130`). |
| `darts_items` | `GameDataManager.dartsItems` | Array; each entry has `id`, `start_date` (`"YYYY-MM-DD HH:MM:SS"`), `items[]`, `extra_item` (`data/MarketplaceInfo.as:190`, `get_game_config.py:225`). |
| `offer_packs` | `GameDataManager.offer_packs` | Array of `OfferPack`. |
| `categories` | `GameDataManager.oItemSubCategories` | Object keyed by category id, each `{id,name,sub:[{id,...}]}` (see the captured payload `config/get_game_config.php_29august2012.txt`). |
| `level_ranking_reward` | `GameDataManager.arIslandsRewards` | Array indexed by `MAX_LEVEL - level`; entries have `units` and `cash` (`newTowns/ExplorationsManager.as:440-443`). |
| `items` | `GameDataManager.items` | Array of static item definitions → `StaticData` (§3.6). |
| `units_collections_categories` | `GameDataManager.unitCollectionCategories` | OData. |
| `findable_items` | `GameDataManager.oFindableItems` | Array of `{id,...}`; keyed by `id`. |
| `levels` | `GameDataManager.arLevelList` | Array of `LevelInfo`; each has `exp_required` and `name` (`managers/GameDataManager.as:94-110`, `managers/PlayerStatus.as:280-281`). |
| `translation_goals` | `GameDataManager.translationGoals` | Optional (null-guarded, `managers/GameDataManager.as:143-146`). |
| `images` | `GameDataManager.localizationImgs` | Optional map `"/<path>" → "<lang-folder>"` used by `core/ImageLoader.as:46`. |
| `expansion_prices` | `GameDataManager.expansionPriceList` | Array. |
| `neighbor_assists` | `GameDataManager.assistList` | Array. |
| `map_prices` | `GameDataManager.townPriceList` | Array. |
| `social_items` | `GameDataManager.socialItemsList` | Array of `{id,...}`; also indexed by `id` into `socialItemsMap`. |
| `missions` | `GameDataManager.missionsList` | Array of `{id,...}` indexed by `id` (`managers/GameDataManager.as:159-162`). **Not present** in the captured 2012 server payloads and not present in the preservation `config/main.json` → `missionsList` ends up empty in practice. |
| `magics` | `GameDataManager.magicList` | Array of `{id,...}` indexed by `id`. |
| `inventory_items` | `GameDataManager.inventoryList` | Array of inventory item defs. |
| `collections` | `GameDataManager.collectionList` | Array of `{id, name, item_ids (JSON string), prize (JSON string), description, cashPrice}` (`managers/GameDataManager.as:174-177`). |
| `sounds` | `new SoundManager(loadedInfo.sounds)` | `core/Base.as:1405`. |
| `goals` | *not read by the client* | present in the payload; consumed server-side. |
| `town_prices` | *not read by the client* | present in the payload. |

Globals referenced by name (partial, all `Base.Items.globals.*`):

`DEPOT_LIMITS` (JSON string), `BASE_RESOURCE_LIMITS` (object keyed by `g/c/o/w/s`,
`managers/PlayerStatus.as:233-237`), `TIMER_NEIGHBOUR` (`core/Base.as:1406`),
`FONT_EQUIVALENCE` (`core/Base.as:1415`), `ENERGY_MAX_REGULAR_VALUE`
(`managers/PlayerStatus.as:313`), `CROSS_ITEMS` + `CROSS_PROMOTIONS`
(`managers/GameDataManager.as:178-179`), `START_MAX_POPULATION`, `MAX_POPULATION`,
`MAX_POPULATION_CAP` (`managers/PlayerStatus.as:390,427,430`), `DART_COST_CASH`
(`managers/PlayerStatus.as:260`), `ALLIANCE_DAILY_BONUS_REWARDS`
(`data/AllianceInfo.as:219`), `PREMIUM_ACCOUNTS` (server-side, `get_game_config.py:182`),
`MONDAY_BONUS_REWARDS` (server-side, `get_game_config.py:199`), `LIMITED_EDITION_EXPIRATION`
(`core/Base.as:7902`), `UPGRADE_SPEEDUP_PRICING` (array `[divisor, price]`,
`core/StaticData.as:333-336`), `URL_APP_PROD` (`core/Base.as:2806`).

### 3.3 `get_player_info.php` (own map)

The client expects a flat object with these top-level keys
(`core/Base.as:1426-1619`, `managers/PlayerStatus.as:285-365`):

```jsonc
{
  "result": "ok",                 // "error" => showErrorSync(ERROR_STOLEN)
  "processed_errors": 0,
  "timestamp": 1349266517,        // server epoch seconds
  "playerInfo": { ... },
  "map":         { ... },
  "privateState":{ ... },
  "neighbors":   [ { ... } ]      // only present for the own-map call
}
```

**`playerInfo`** (read in `managers/PlayerStatus.as:288-302` and `core/Base.as:1501-1503`):

| Field | Type | Use |
|---|---|---|
| `pid` | String | player uid (used by alliance/world lookups) |
| `name` | String | empire name |
| `pic` | String | avatar URL |
| `cash` | Number | premium currency → `PlayerStatus.iCash` (`managers/PlayerStatus.as:238`) |
| `default_map` | Number | → `PlayerStatus.iDefaultMap` (= `Base.Main.townID`, `managers/PlayerStatus.as:267`, `core/Base.as:1499`) |
| `map_names` | Array[String] | town names; length = number of towns |
| `map_sizes` | Array[Number] | per-town size; `>0` counts as an owned town (`core/Base.as:1501-1509`) |
| `world_id` | Number | fallback world id when `map.id == 0` (`managers/PlayerStatus.as:268-275`) |
| `sp_ref_uid` | Number | install-tracking uid (see §10.4) — **not read by this SWF** |
| `sp_ref_cat_install` | String | install-tracking category — **not read by this SWF** |
| `last_logged_in` | Number | server-side bookkeeping |
| `completed_tutorial` | Number | server-side bookkeeping |

**`map`** (read in `managers/PlayerStatus.as:290-302`, `core/Base.as:1493-1554`, `core/Base.as:7151-7153`):

| Field | Type | Use |
|---|---|---|
| `id` | Number | map index; `0` ⇒ own primary map (`managers/PlayerStatus.as:268-275`) |
| `world_id` | Number | → `PlayerStatus.worldId`; `universeId = ceil(worldId/1000000)` (`managers/PlayerStatus.as:231`) |
| `gold`, `steel`, `wood`, `oil` | Number | resources |
| `xp` | Number | experience (`parseInt`) |
| `level` | Number | player level |
| `race` | String | `"h"` (human) / `"t"` (troll) — compared against `building.race` (`core/Base.as:6391`) |
| `skin` | Number | → `Base.Main.skinMap` (background skin index) |
| `resourcesTraded` | Object | per-resource trade counters |
| `expansions` | Array[Number] | owned map tiles → `Base.Main.ownedGrid` (`core/Base.as:1552-1553`, `core/Base.as:7171-7175`) |
| `items` | Object | map contents, keyed by iso-id (§3.5) |
| `receivedAssists` | Object | assist counters per friend |
| `increasedPopulation` | Number | optional, defaults to 0 |
| `expirableUnitsTime` | Object | special-unit expiry timestamps |
| `currentQuestVars` | Object | quest state machine variables → `Base.Main.currentQuestProperties` (`managers/PlayerStatus.as:292`) |
| `idCurrentMission` | Number | current chapter id (`core/Base.as:1493`) |
| `timestampLastChapter` | Number | (`core/Base.as:1498`) |
| `store` | Object | building storage, id → qty |
| `universAttackWin` | Array | islands/continents conquered (`newTowns/ExplorationsManager.as:378-382`) |
| `idCurrentTreasure`, `timestampLastTreasure` | Number | treasure chest state |
| `resourceAlliesMarket` | Object | ally-market resources |
| `timestampLastTrade`, `numTradesDone` | Number | daily trade reset |

**`privateState`** (read in `managers/PlayerStatus.as:291,303-361` and `core/Base.as:1529-1615`):

| Field | Type | Use |
|---|---|---|
| `mana` | Number | → `PlayerStatus.iMana` |
| `energy` | Number | → `PlayerStatus.iEnergy`; if below `ENERGY_MAX_REGULAR_VALUE` the client sends `modify_energy` (`managers/PlayerStatus.as:312-320`) |
| `inventoryItems` | Object | item id → qty (string keys) → `Inventory` |
| `collections` | Array | collection completion state |
| `goals` | Object | goal progress → `GoalManager.initData` |
| `researchItemNumber`, `researchStepNumber`, `timeStampDoResearch` | Object/Array | research centre state |
| `publishedOpenGraphUnit` | Array | ids already published |
| `timeStampEndPremium` | Number | premium account expiry (`managers/PlayerStatus.as:240`) |
| `unlockedSkins` | Object | `managers/PlayerStatus.as:249` |
| `unlockedQuestIndex` | Number | `managers/PlayerStatus.as:250` |
| `questsRank` | Object | `managers/PlayerStatus.as:251` |
| `magics` | Object | learned magics (`managers/PlayerStatus.as:252`) |
| `timeStampDartsReset`, `timeStampDartsNewFree` | Number | darts minigame |
| `dartsBalloonsShot` | Array | darts state |
| `dartsRandomSeed`, `dartsHasFree`, `dartsGotExtra` | Number/Boolean | darts state |
| `boughtUnits` | Array | `managers/PlayerStatus.as:265` |
| `unitCollectionsCompleted` | Array | `managers/PlayerStatus.as:266` |
| `neighborAssists` | Object | `"u<pid>"` → timestamp; the client also accepts a bare `<pid>` key (`core/Base.as:1529-1537`) |
| `friendsHelpedCoveredItem` | Number | `core/Base.as:1551` |
| `lastUpgrades` | Array[Number] | upgrade timestamps → daily upgrade counter (`core/Base.as:1568-1575`) |
| `timestampLastBonus` | Number | daily bonus readiness |
| `timeStampMondayBonus` | Number | weekly (Monday) bonus |
| `timestampLastAllianceBonus` | Number | alliance daily bonus |
| `bestUnit` | Object | `{iid: Number}` → `AllianceInfo.userBestUnitId` (`core/Base.as:1606-1613`) |
| `firstTimeAlliance` | Boolean | `AllianceInfo.introduced` |
| `marketPlaceFirstTime` | Boolean | `MarketplaceInfo.marketplaceTutorialShowed` |
| `strategy` | Number | defensive strategy, read in assault mode (`core/Base.as:7187`) |
| `message` | String | server mailbox message |
| `betWin` | Array | `{iid, level[]}` → marketplace wins (`core/Base.as:7644-7662`) |
| `attacksSent`, `attacksReceived` | Array | `{time, victim_id, alliance_used}` (`core/Base.as:7676-7722`) |
| `tsAttacksReset`, `tsSpyingsReset` | Number | attack/spying timers |
| `attacksPack`, `spyingsPack` | Number | |
| `deadHeroes` | Object | resurrectable heroes |
| `crossPromotionsFinished` | Array | `managers/PlayerStatus.as:371-377` |
| `helpMap`, `worldChange`, `bonusNextId` | Object/Number | server-side |

**`neighbors[]`** (own-map call only) — `core/Base.as:1513-1550`:

| Field | Type | Use |
|---|---|---|
| `pid` | String | neighbour uid |
| `name` | String | empire name |
| `xp` | Number | |
| `level` | Number | |
| `world_id` | Number | `neighbor.world_id` |

The client then computes `neighbor.assist = "1"` if
`timestamp - privateState.neighborAssists["u"+pid] > 24*3600` (`core/Base.as:1538-1546`).
`neighbor.pic` is taken from the **flashvar** `friendsInfo` map (`friend.pic_square`),
not from the server (`core/Base.as:1520-1526`).

### 3.4 `get_player_info.php` (neighbour / quest / assault map)

Same top-level shape but **without** `neighbors` (the preservation server omits it too,
`get_player_info.py:34-41`), and with `map` replaced by the *target's* map.
The client then branches on `Base.Main.gameMode`
(`core/Base.as:7177-7208`):

* `GAME_MODE_NEIGHBOUR` → `Base.Gui.setNeighborStats(_loc5_)`
* `GAME_MODE_ASSAULT` → `Base.Gui.setAssaultStats(_loc5_.playerInfo, _loc5_.map)` and
  `Assault.setDefensiveStrategy(_loc5_.privateState.strategy)` (non-quest only)
* `GAME_MODE_NORMAL` → `Base.Player.load(_loc5_); Base.Player.Init();` and
  `this.lastServerTimestamp = _loc5_.timestamp`

### 3.5 `map.items` — the map item tuple

`map.items` is a **Dictionary** keyed by the item's iso-id (string), each value an
**array** (`core/Base.as:6263-6337`):

| Index | Meaning | Default when absent |
|---|---|---|
| `[0]` | item id (matches `Base.Items.items` → `StaticData.id`) | — |
| `[1]` | tile X (`tx`) | — |
| `[2]` | tile Y (`ty`) | — |
| `[3]` | activation timestamp (unix seconds) | `0` |
| `[4]` | frame / orientation | `0` |
| `[5]` | contained units array | `[]` |
| `[6]` | attributes object | `{}` |
| `[7]` | `playerID` (`1`=self, `2`=enemy, `3`=neutral, `0`=undecided) | `Constants.PLAYER_SELF` |
| `[8]` | extra int (imgIndex / build-finish) | `0` |

The attributes object `[6]` carries `nc` (clicks to build), `si` (socially in
construction), `nu` (queued units), `ts`, `ui`, `xp` — see the preservation server's
`engine.py:125-213`, which manipulates exactly these keys.

The client re-materialises the tuple into a flat 20-slot array
(`core/Base.as:6370`): `[null, tx, ty, id, frame, ? , activation, 0, collect_xp,
collect, collect_type, category_id, 1, ?, units, attrs, playerID, isoId, ?, attrs.xp]`.

### 3.6 `StaticData` — the `items[]` record

Parsed in `core/StaticData.as:125-230`. Field names consumed from the server:

`id`, `name`, `type` (`"b"` building / `"u"` unit — `core/Constants.as:1666,1668`),
`cost_unit_cash`, `xp`, `display_order`, `activation`, `expiration`, `collect`,
`collect_type`, `collect_xp`, `category_id`, `subcategory_id`, `subcategory2_id`,
`subcat_functional`, `min_level`, `width`, `height`, `in_store`, `new_item`,
`max_frame`, `img_name` (Vector **or** comma-separated String —
`core/StaticData.as:242-267`), `elevation`, `unit_capacity`, `attack`, `defense`,
`life`, `velocity`, `attack_range`, `attack_interval`, `population`, `race`,
`protect`, `best_against`, `best_against_mult`, `building_limit_same_scf`,
`building_limit_same_id`, `properties` (JSON string **or** object),
`inventory_ids` (JSON string **or** object), `costs` (JSON string **or** object),
`trains_ids`, `training_time`, `upgrades_to`, `syringes`, `max_collects`,
`breeding_order`, `sm_training_time`, `build_time`, `gid`, `frame`, `cash`,
`group_type`, `clicks_to_build`.

### 3.7 `DynamicData` — the per-item dynamic record

`core/DynamicData.as:44-73`: `quest_id`, `x`, `y`, `id`, `orientation`,
`collected_at`, `activation`, `expiration`, `collect_xp`, `collect`, `collect_type`,
`category_id`, `active`, `level`, `units` (Array), `attrs` (Object),
`playerID`, `isoId`, `imgIndex`.

### 3.8 `command.php` response

`managers/CommandManager.as:419-476`. The body is plain JSON (no hash prefix is
stripped here — `Crypto.getHashAndPayload` is *not* used for command responses):

```jsonc
{ "result": "success" }
```

or

```jsonc
{ "result": "error", "error": "<code>", "description": "<human readable>" }
```

Recognised `error` codes → client error class:

| `error` value | Client constant | Source |
|---|---|---|
| `client_id` | `ERROR_STOLEN` | `managers/CommandManager.as:437-440` |
| `no_client_id` | `ERROR_SERVER_STOLEN` | `managers/CommandManager.as:441-444` |
| `hash` | `ERROR_CLIENT_HASH` | `managers/CommandManager.as:445-448` |
| `user_key` | `ERROR_STOLEN` | `managers/CommandManager.as:449-452` |
| `json` | `ERROR_UNKNOWN` | `managers/CommandManager.as:453-456` |
| `timehack` | `ERROR_TIME_HACK` (returns early) | `managers/CommandManager.as:458-464` |
| `bad_flash_version` | `ERROR_BAD_FLASH_VERSION` | `managers/CommandManager.as:465-468` |
| anything else | `ERROR_SYNC` | `managers/CommandManager.as:433,470` |

A response that is neither (`result` missing / unparseable / empty body) is treated as a
**timeout** and the packet is retried (`managers/CommandManager.as:472-475`).

### 3.9 `get_public_player_info.php` response

`popups/PopupPlayerProfile.as:93-130`: parsed as plain JSON, then
`last_logged_in` (unix seconds) is read; `fillPopup()` also uses rank/victory/defeat
fields. Exact field set **UNVERIFIED** beyond `last_logged_in` — the rest of the popup
reads fields that this file does not spell out in the excerpt.

### 3.10 `get_user_world.php` response

`popups/PopupAttackFinished.as:553-566`:

```jsonc
{ "result": { "world_id": 12345678 } }   // world_id == 0 => "Couldn't find player"
```

Note the nesting: `result` is an **object** here, not a string.

### 3.11 `get_continent_ranking.php` response

`newTowns/ExplorationsManager.as:404-446`:

```jsonc
{
  "world_id": 12345678,                 // optional
  "continent": [ { "nivel": 3, "posicion": 2, "user_id": "..." }, ... ]
}
```

`nivel` = level, `posicion` = slot, `user_id` = the player who owns that slot.

### 3.12 Alliance responses

* `alliance-info` → `{"success":1, "alliance": { id, owner_id, title, description,
  points, rating, members, free_slots, date_create, members:[ {id,user_id,last_login,...} ] }}`
  — `data/AllianceInfo.as:170-234`.
* list endpoints → `{"success":1, "list":[...], "pager":{ pageNo, ... }}`
  — `popups/alliances/AllianceState.as:513-539`.

### 3.13 Bets responses

* `get_bets_list.php` → `{"bets":[ {uuid, idUnit, level, beginDate, endDate, beginPrice,
  currentPrice, priceIncrement, betPrice, round, isPrivate, isWinning, won, finished,
  bidders:[...], prevRoundBidders:[...] } ]}` — `data/MarketplaceUnitInfo.as:48-77,244-272`.
  Bidders are objects with `user_id` and `bet` (`data/MarketplaceUnitInfo.as:221,286`).
* `get_bet_detail.php` → `{"betDetail":{...}, "betUsers":[...], "betUsersPrev":[...],
  "betWinner":"<uid>"}` — `data/MarketplaceUnitInfo.as:166-180`.

---

## 4. `command.php` wire format

### 4.1 Framing

`core/Crypto.as:48-51`:

```as3
public static function constructHashAndPayload(param1:String, param2:String) : String
{
   return Hex.fromArray(hash(param1,param2)) + ";" + param1;
}
```

* **Prefix:** 64 lowercase hex characters = the HMAC-SHA256 digest of the payload.
* **Separator:** a single `;` (U+003B) at offset 64.
* **Payload:** the raw JSON string, *not* escaped.
* The body field name is `data`; the value is `"<64 hex>;<json>"`.

Parsing side (`core/Crypto.as:29-46`):

```as3
var _loc2_:RegExp = /^([0-9a-f]{64});(.*)$/i;
```

If the regex does not match (e.g. a plain, un-hashed JSON body), the function returns
`{hash: null, payload: <the whole input>}`. This is what makes
`skiphash12341` work with a hash-less server response.

### 4.2 JSON body

`managers/CommandManager.as:389-397`:

```as3
_loc5_.data = Crypto.constructHashAndPayload(com.adobe.serialization.json.JSON.encode({
   "first_number":param1.firstNumber,
   "commands":param1.commands,
   "tries":param1.tries,
   "publishActions":(Base.Main.publishActions ? "1" : "0"),
   "ts":_loc2_,
   "flashVersion":Config.VERSION,
   "accessToken":Base.Player.accessToken
}),Config.SERVER_KEY);
```

| Field | Type | Meaning |
|---|---|---|
| `first_number` | Number | Sequence number of the **first** command in the packet. Starts at 1, and after each packet `nextCommandNumber += commands.length` (`managers/CommandManager.as:375`). Reset to 1 whenever the player returns to their own map (`core/Base.as:6970`, `core/Base.as:1448`). The server uses it to detect gaps/duplicates. |
| `commands` | Array | The per-command tuples (§4.3). |
| `tries` | Number | 1-based attempt counter for this packet; incremented on every `sendPacket` (`managers/CommandManager.as:382`). |
| `publishActions` | `"0"`/`"1"` | Open-Graph publishing enabled (flashvar `publishActions`, `core/Base.as:1182-1185`). |
| `ts` | Number | Server-synchronised epoch seconds: `lastServerTimestamp + (getTimer()/1000 - _secondsServerReceived)` (`core/Base.as:2793-2797`). Used by the server for anti-time-hack checks (server error `timehack`). |
| `flashVersion` | String | `Config.VERSION` = `"1.5.4"` (`core/Config.as:8`). The server may reject with `bad_flash_version`. |
| `accessToken` | String | The Facebook OAuth access token, taken from flashvar `accessToken` (`managers/PlayerStatus.as:306`). |

### 4.3 Per-command tuple

`core/Command.as:113-116`:

```as3
public function serialize() : Array
{
   return [Base.Main.townID, this.commandID, this.args, this.resourcesVariation];
}
```

So each element of `commands` is a **4-element JSON array**:

```
[ 0 ] map_id             Number  -> Base.Main.townID == Base.Player.iDefaultMap == playerInfo.default_map
[ 1 ] cmd                String  -> the command id, e.g. "buy", "move", "attack_player"
[ 2 ] args               Array   -> positional arguments, MIXED types
[ 3 ] resources_changed  Array[8]  -> resource deltas
```

**`args` encoding.** `args` is a plain JSON array whose elements are heterogeneous:
numbers, strings, and *strings containing JSON* (nested objects are `JSON.encode`d
before being pushed, so they arrive as JSON **strings**, not nested JSON objects).

Examples (`core/Command.as` subclasses):

| cmd | args |
|---|---|
| `buy` | `[isoId, itemId, tx, ty, playerID, frame, isAutoActivatable(0/1), buildingType]` — `commands/CmdBuy.as:26-33` |
| `move` | `[isoId, tx, ty, frame, "<debug label>"]` — `commands/CmdMove.as:18-21` |
| `attack_player` | `[targetUid]` — `commands/CmdAttackPlayer.as:9` |
| `spy_player` | `[targetUid]` — `commands/CmdSpyPlayer.as` |
| `place_stored_item` | `[isoId, itemId, tx, ty, playerID, frame, flag, imgIndex, (level+1, requiredXp)?]` — `commands/CmdPlaceStoredItem.as:28-43` |
| `set_quest_var` | `[key, JSON.stringify(value)]` — `commands/CmdSetQuestVar.as:11` |
| `set_goals` | `[goalId, JSON.stringify([visited, currentStep])]` — `commands/CmdSetGoals.as` |
| `assist_neighbor` | `[uid, JSON.stringify(array)]` — `commands/CmdAssistNeighbour.as:19` |
| `end_attack` | `[JSON.stringify(resultObj), "1"|"0"]` — `commands/CmdEndAttack.as:14-15` |
| `end_quest` | `[JSON.stringify(resultObj)]` — `commands/CmdEndQuest.as:18` |
| `activate_item_click` | `[isoId, JSON.stringify(obj)]` — `commands/CmdActivateItemClick.as` |
| `store_item` | `[isoId]` — `commands/CmdStoreItem.as` |
| `collect` | `[isoId]` — `commands/CmdCollect.as` |
| `weekly_reward` | `[isoId, buildingId, 0, 0, playerID]` — `commands/CmdCollectMondayBonus.as` |
| `flash_debug` | `[cash, energy, xp, gold, oil, steel, wood]` — `commands/SystemCmdDebugResources.as:11-17` |
| `ping` | `[]` — `commands/CmdPing.as` |
| `set_variables` | `[]` — `commands/AdminCmdSetVariables.as` |
| `rt_open_graph_unit` | `[itemId]` — `commands/CmdNewOpenGraphUnit.as` |
| `trade_resource` | `[resourceId, ...]` — `commands/CmdTradeResource.as` |

Full list of command ids present in the binary (from `super("…")` in
`scripts/commands/*.as`):

```
accept_collect_help, activate, activate_item_click, add_click, add_inventory_item,
add_xp_unit, admin_set_quest_rank, apply_rewards_ranking, assist_neighbor,
assist_receive, attack_player, batch_remove, buy, buy_magic, buy_mana_new,
buy_offer_pack, buy_premium_account, buy_resources, buy_si_help,
buy_stored_item_cash, clean_attacks, clean_received_assists, clear_message, collect,
collect_mission, complete_collection, complete_goal, complete_tutorial,
cross_promotion_finished, darts_new_free, darts_reset, darts_shoot_balloon, end_attack,
end_quest, exchange_cash, expand, fast_forward, finish_building, finish_robotic_help,
finish_si, flash_debug, kill, kill_iid, level_up, load_map, modify_energy,
modify_position_universe, move, next_research_item, next_research_step, orient, ping,
place_gift, place_stored_item, pop_queue_unit, pop_unit, premium_upgrade,
push_queue_unit, push_queue_unit2, push_unit, buy_powerups, rt_open_graph_unit,
receive_mana(system_receive_mana), remove_inventory_item, research_buy_step_cash,
reset, reset_collect, reset_position_univers, reset_research_item, reset_world_change,
resurrect_hero, save_map, sell, sell_gift, sell_stored_item, set_goals, set_help_map,
set_quest_var, set_resource_allies, set_strategy, soulmixer_speedup, spy_player,
store_add_items, store_item, system_receive_si_help, system_reset_quest, trade_resource,
unit_collections_completed, upgrade, use_magic, weekly_reward, win_daily_bonus
```

Note the two truncated/legacy ids in the original: `reset_position_univers`
(`commands/CmdResetPositionUniverse.as`) and `system_receive_mana`
(`commands/CmdReceiveMana.as`) — reproduce them verbatim.

**Legacy alternative command shape.** `CommandManager.add(cmd, ...args)`
(`managers/CommandManager.as:191-201`) pushes `{"cmd": <name>, "args": [...]}` — an
**object** instead of the 4-tuple. No call site exists in the decompiled code
(`grep "Commands.add("` → no matches), so it is dead code, but it proves the original
server accepted both shapes. `UNVERIFIED` whether the original PHP accepted both.

### 4.4 `resources_changed` — the 8-slot delta vector

`core/Command.as:8-24` and `core/Command.as:51-111`:

| Index | Constant | Resource letter |
|---|---|---|
| 0 | `RESOURCE_ENERGY` | `e` |
| 1 | `RESOURCE_XP` | `x` |
| 2 | `RESOURCE_GOLD` | `g` |
| 3 | `RESOURCE_WOOD` | `w` |
| 4 | `RESOURCE_OIL` | `o` |
| 5 | `RESOURCE_STEEL` | `s` |
| 6 | `RESOURCE_CASH` | `c` |
| 7 | `RESOURCE_MANA` | `m` |

Slot 0 is energy (the preservation server calls it "unknown",
`engine.py:253`, but it is energy). Deltas are **signed**; spending produces negative
values. `Command.involvesCash` is true when slot 6 != 0
(`core/Command.as:123-126`) and triggers an immediate flush (10 ms) of the command
queue (`managers/CommandManager.as:171-189`).

The preservation server applies them with
`map["xp"] = max(map["xp"]+xp, 0)` etc. and treats a negative result as a cheat signal
(`engine.py:251-269`).

---

## 5. Command execution model

### 5.1 Queueing

`managers/CommandManager.as:154-183` (`queueCommand`):

* A command is only queued when
  `param2 == true` **or** (`gameMode == GAME_MODE_NORMAL` **or**
  (`gameMode == GAME_MODE_NEIGHBOUR` and the command is a `CmdAssistNeighbour`)).
  `param2` is the "force" flag used for commands that must reach the server in other
  modes (spying, attacks, energy top-up, island repositioning…).
* Before queuing, `Base.Resources.adjustResourcesByCommand(cmd)` applies the predicted
  resource delta locally so the UI is immediately consistent.
* `cmdCount % 20 == 0` and player level ≥ 10 → a `SystemCmdDebugResources`
  (`flash_debug`) command is injected (`managers/CommandManager.as:158-161`,
  `DEBUG_CMD_COUNT = 20` at `managers/CommandManager.as:59`).
* `debugResources` mode adds a `resources` map (`{w,s,o,g,c,x}`) to the command object
  (`managers/CommandManager.as:166-169`, `managers/PlayerStatus.as:613-623`).

### 5.2 Batching / flushing

* Main flush timer: `Timer(Base.Main.push_time * 1000)` — `push_time` comes from the
  flashvar `push_time`, clamped to **[3, 60]** seconds, default `Config.TIMER_COMMANDS = 6`
  (`core/Base.as:998-1013`, `core/Config.as:118`, `managers/CommandManager.as:147-149`).
* Unit-movement timer: `Timer(Config.TIMER_UNITMOVE_COMMANDS)` = **6000 ms**
  (`core/Config.as:120`, `managers/CommandManager.as:117,150-151`); it emits `move`
  commands for units that moved since the last server update
  (`managers/CommandManager.as:203-226`).
* Cash commands trigger an extra one-shot `Timer(10,1)` flush
  (`managers/CommandManager.as:171-189`).
* `sendCommands()` (`managers/CommandManager.as:325-378`):
  * bails out if `Base.Main.bLargeStore` or if the manager is `locked`
    (the manager is locked while a neighbour/quest map is being loaded —
    `core/Base.as:6972`, `core/Base.as:7131`);
  * if a packet is already in flight, only the timeout check runs;
  * otherwise all pending commands (plus accumulated unit XP, see
    `addSendUnitsXPCommands`, `managers/CommandManager.as:277-290`) are moved into a
    single `CommandPacket` and sent as **one** request;
  * `nextCommandNumber += commands.length` after the send.
* `Base.Commands.lock()` / `unlock()` and `callbackFunctionServer` implement a
  "flush before navigating" pattern: `realLoadMap` sets
  `callbackFunctionServer = this.realLoadMap` and calls `sendCommands()`, so the pending
  commands are delivered before the client asks for another map
  (`core/Base.as:6946-6950`, `core/Base.as:6959-6967`).

### 5.3 Retries and "tries"

* `sendPacket` increments `packet.tries` (1-based) and refreshes `packet.timestamp`
  (`managers/CommandManager.as:382-384`).
* A packet is considered **timed out** when more than **30 s** have elapsed since it
  was sent, or when an `IOErrorEvent` was received (`managers/CommandManager.as:352-360`).
* `processCommandsTimeout()` re-sends the *same* packet (same `first_number`, same
  commands) with `tries` incremented; after `tries >= 3` it gives up and raises
  `ERROR_TIMEOUT` (`managers/CommandManager.as:478-490`).
* `ioErrorHandlerCommands` only sets `currentPacket.ioError = true`
  (`managers/CommandManager.as:492-495`); the actual retry happens on the next timer tick.
* **Session expiry:** if more than **2700 s** (45 min) elapsed since the last successful
  command send, `showErrorSync(ERROR_EXPIRED)` is raised
  (`managers/CommandManager.as:342-351`).
* The `tries` counter is also transmitted in the JSON body and in
  `sync_error_track.php`, so the server can correlate retries.

### 5.4 Error taxonomy

`managers/CommandManager.as:35-55`:

```
ERROR_UNKNOWN          "unknown"
ERROR_TIMEOUT          "timeout"
ERROR_SYNC             "sync"
ERROR_EXPIRED          "expired"
ERROR_STOLEN           "stolen"
ERROR_SERVER_STOLEN    "server_stolen"
ERROR_SERVER_HASH      "server_hash"
ERROR_CLIENT_HASH      "client_hash"
ERROR_PLAYER_INFO      "player_info"
ERROR_TIME_HACK        "time_hack"
ERROR_BAD_FLASH_VERSION "bad_flash_version"
```

`showErrorSync` (`managers/CommandManager.as:497-564`) stops the command timer, POSTs
the telemetry to `sync_error_track.php`, **clears `phpsessid`** (`managers/CommandManager.as:539`),
shows a modal alert, and on OK navigates the browser to
`Base.Main.canvasAddress + "?sp_ref_cat=flash_sync_error"`
(`managers/CommandManager.as:566-570`, constant at `managers/CommandManager.as:57`).

`ERROR_SERVER_HASH` is raised when the *server's* response to `get_player_info.php`
fails the client's hash check (`core/Base.as:7142-7146`).

---

## 6. Cryptography / hashing

### 6.1 The primitive

`core/Crypto.as:16-20`:

```as3
public static function hash(param1:String, param2:String) : ByteArray
{
   var _loc3_:HMAC = new HMAC(new SHA256());
   return _loc3_.compute(stringToByteArray(param2), stringToByteArray(param1));
}
```

* `HMAC` = `com/hurlant/crypto/hash/HMAC.as` (classic ipad/opad HMAC, 64-byte block).
* `SHA256` = `com/hurlant/crypto/hash/SHA256.as` + `SHABase.as` — a **standard** FIPS 180-4
  SHA-256 (verified: the `k` table and the initial `h` vector are the standard ones).
* Argument order: `compute(key, message)`; the call site passes
  `compute(stringToByteArray(param2), stringToByteArray(param1))`, i.e.
  **key = `param2`, message = `param1`**.

### 6.2 The `writeUTFBytes` twist (IMPORTANT)

`core/Crypto.as:22-27`:

```as3
public static function stringToByteArray(param1:String) : ByteArray
{
   var _loc2_:ByteArray = new ByteArray();
   _loc2_.writeUTFBytes(param1);
   return _loc2_;
}
```

`ByteArray.writeUTFBytes()` writes a **2-byte big-endian UTF-8 length header** before
the UTF-8 bytes. Therefore the effective HMAC inputs are **not** the raw strings:

```
key_bytes    = uint16_be(len(utf8(key)))    || utf8(key)     , zero-padded to 64
message_bytes= uint16_be(len(utf8(payload))) || utf8(payload)
digest       = HMAC-SHA256(key_bytes[0:64], message_bytes)
```

Reference implementation (Python):

```python
import hmac, hashlib

def as3_write_utf_bytes(s: str) -> bytes:
    b = s.encode("utf-8")
    return len(b).to_bytes(2, "big") + b

def crypto_hash(payload: str, server_key: str) -> bytes:
    key = as3_write_utf_bytes(server_key)
    if len(key) > 64:
        key = hashlib.sha256(key).digest()
    key = key.ljust(64, b"\x00")
    msg = as3_write_utf_bytes(payload)
    return hmac.new(key, msg, hashlib.sha256).digest()

def construct_hash_and_payload(payload: str, server_key: str) -> str:
    return crypto_hash(payload, server_key).hex() + ";" + payload
```

**Caveat — `UNVERIFIED` / practical limit:** `writeUTFBytes` throws
`RangeError #1030` for payloads longer than 65535 UTF-8 bytes, so the client's
`Crypto.checkHashAndPayload()` **cannot verify the 945 KB `get_game_config.php`
response**. The client never notices because the response is only *verified* when the
flashvar `skiphash12341` is absent (`core/Base.as:1355`, `core/Base.as:1452`,
`core/Base.as:7142`), and the preservation server sets `skiphash12341=notnull`
(`templates/play.html:91`). The original Zynga server clearly *did* emit a hash
prefix for the config response — the captured payloads in
`config/get_game_config.php_23july2012.txt` and `..._29august2012.txt` both begin
with 64 hex chars + `;`.

**`UNVERIFIED`:** the exact key used by the original Zynga server for those 2012
captures. The SWF's `Config.SERVER_KEY` is `"4vVSD8dftv6hdfb1Hnk9"`
(`core/Config.as:72`), but **none** of the following reproduce the captured digests:
standard `HMAC-SHA256(key, payload)`, `SHA256(payload||key)`, `SHA256(key||payload)`,
`HMAC-SHA1`, `HMAC-MD5`, the `writeUTFBytes`-prefixed key variant, UTF-16 key
encodings, or `HMAC(md5(key), payload)`. The captured files are most likely from a
different (earlier) build with a different `SERVER_KEY`, or the key was rotated.
**The preservation server therefore does not verify the hash at all**
(`server.py:321-325` just strips the first 64 chars and the `;`).

### 6.3 `user_key`, `accessToken`, `client_id`

| Token | Where it comes from | Where it is used |
|---|---|---|
| `USERID` / `phpsessid` | flashvar `fb_sig_user` → `CommandManager.phpsessid` (`core/Base.as:1086-1089`); cleared to `""` on any sync error (`managers/CommandManager.as:539`) | query string on every dynamic request (`managers/CommandManager.as:586,590`); `userId` field in every alliance/bet body; `user_id` in `sync_error_track.php` |
| `user_key` | flashvar `user_key` → `CommandManager.userKey` (`core/Base.as:1094-1097`) | query string `&user_key=…` on every dynamic request; also `session_id` in `bets/set_bet.php` (`popups/marketplace/PopupMarketplaceUnit.as:341`); the server may reject with `error: "user_key"` (`managers/CommandManager.as:449-452`) |
| `accessToken` | flashvar `accessToken` → `PlayerStatus.accessToken` (`managers/PlayerStatus.as:306`) | inside the `command.php` JSON body (`managers/CommandManager.as:396`) so the server can publish Open-Graph actions on the player's behalf |
| `client_id` | random per session: `Math.round(Math.random()*1073741824)` (`core/Base.as:887`) | body of `command.php` (`managers/CommandManager.as:398`) and of `get_player_info.php` (`core/Base.as:1409`); the server can reject with `error:"client_id"` (stolen session) or `error:"no_client_id"` (server lost the session) |
| `install_id` | flashvar `install_id` → `track_game_status.php` body `installId` (`core/Base.as:7962-7971`) | install tracking |

### 6.4 `skiphash12341`

`skiphash12341` is a **debug bypass flashvar**. It appears exactly three times, always
in the same guard:

```as3
if (this.getStage().loaderInfo.parameters["skiphash12341"] == null
    && !Crypto.checkHashAndPayload(hashAndPayload, Config.SERVER_KEY)) { ...fail... }
```

* `core/Base.as:1355` — `loadGameConfigSuccess` (on failure: reports the error and returns).
* `core/Base.as:1452` — `loadPlayerInfoSuccess` (on failure: returns silently).
* `core/Base.as:7142` — `loadMapHandler` (on failure: `showErrorSync(ERROR_SERVER_HASH)`).

Meaning: **if the flashvar is present (any value, even `"notnull"`), the client accepts
responses without verifying the HMAC.** The literal `12341` is a Social Point internal
ticket number, not a cryptographic value. The preservation server relies on this
(`templates/play.html:91`) and serves `config/main.json` **without** a hash prefix.

---

## 7. Game config loading (`get_game_config.php`)

Flow (`core/Base.as:1334-1424`):

1. `mainLoaded()` → `Base.Commands.Init1()` (sets `baseURL`, `sessionID`, `commandBase`)
   → `Base.Commands.getInfo(Config.SERVICE_GET_GAME_CONFIG, null, this.loadGameConfigSuccess)`.
2. `loadGameConfigSuccess`:
   * `Crypto.getHashAndPayload(e.currentTarget.data)` strips the optional `<hash>;` prefix;
   * unless `skiphash12341` is set, `Crypto.checkHashAndPayload()` must pass, otherwise
     the client reports `"Signature Verificaion failed"` and aborts (`core/Base.as:1355-1367`);
   * `resultJson = hashAndPayload.payload`; if empty → error popup
     `"We're experiencing problems with our servers, please check back later. 1"`;
   * `JSON.decode(resultJson)` → `loadedInfo`;
   * if `loadedInfo.result == "error"` → error popup `"…later. 2"` (`core/Base.as:1394-1399`);
   * progress → 50 %;
   * `Base.Items.load(loadedInfo)` (`managers/GameDataManager.as:120-180`);
   * `Base.Sound = new SoundManager(loadedInfo.sounds)`;
   * `this.neighbourTimer = new Timer(Base.Items.globals.TIMER_NEIGHBOUR)`;
   * then `get_player_info.php` is requested (progress 50 → 66 %).

`GameDataManager.load()` expects the top-level sections listed in §3.2. The
`globals` object is mandatory (it is dereferenced immediately). `globals.DEPOT_LIMITS`
must be a **JSON-encoded string** (it is `JSON.decode`d at
`managers/GameDataManager.as:130`).

`items[]` entries are turned into `StaticData` objects; `costs`, `properties` and
`inventory_ids` may arrive either as a JSON **string** (then decoded) or as a real
JSON object (`core/StaticData.as:178-217`).

The preservation server serves `config/main.json` (top-level keys verified):
`categories, items, inventory_items, expansion_prices, levels, neighbor_assists,
town_prices, map_prices, findable_items, goals, offer_packs, social_items, globals,
images, sounds, collections, level_ranking_reward, darts_items,
units_collections_categories, magics`.
**Missing vs. the client contract:** `missions` and `translation_goals`.
`translation_goals` is null-guarded by the client; `missions` is not, but the
2012 captured original payloads also lack it, so this matches the original.

---

## 8. Player info / map state, and the three map flavours

### 8.1 Own map

`core/Base.as:1416` → `get_player_info.php` with `neighbors` + `client_id`.
`core/Base.as:1426-1619` (`loadPlayerInfoSuccess`):

* `Base.Commands.nextCommandNumber = 1` (command sequence restarts).
* `Base.Player.load(loadedInfo)` (`managers/PlayerStatus.as:285-365`).
* `currentQuestId = loadedInfo.map.idCurrentMission` (min 1).
* `timestampLastChapter = loadedInfo.map.timestampLastChapter`.
* `townID = Base.Player.iDefaultMap` (= `playerInfo.default_map`).
* Town count = number of entries in `playerInfo.map_sizes` that are `> 0`.
* `neighbors[]` → `this.friends[]` with `{pid, fbid, name, pic, xp, level, assist, world_id}`.
* `ownedGrid = loadedInfo.map.expansions` → `prepareAvailableGrid()`.
* `processMap(loadedInfo.map.items, loadedInfo.timestamp)` builds the iso scene.
* `lastServerTimestamp = loadedInfo.timestamp` (or the flashvar `serverTime` if present,
  which then forces `bForcedServerTime = true` — `core/Base.as:1556-1565`).
* Daily/weekly bonus state, alliance daily bonus, best unit, marketplace tutorial flag.

### 8.2 Neighbour map vs quest map vs assault map

All three are loaded by the **same** endpoint (`get_player_info.php`) but with different
parameters and different client state.

| | Neighbour map | Quest map | Assault (PvP) map |
|---|---|---|---|
| Trigger | `Base.Main.loadMap(friendUid, "0", Constants.GAME_MODE_NEIGHBOUR)` — `popups/PopupVisit.as:69`, `popups/alliances/AllianceState.as:202` | `Base.Main.loadMap(questUid, "", Constants.GAME_MODE_ASSAULT)` — `quest/Quest.as:262` | `Base.Main.loadMap(targetUid, targetMap, Constants.GAME_MODE_ASSAULT, isSpy)` — `popups/popupLoadingAssault.as:75,229`, `battle/Assault.as:748` |
| `gameMode` | `GAME_MODE_NEIGHBOUR` = 2 | `GAME_MODE_ASSAULT` = 3 **and** `bModeQuest = true` | `GAME_MODE_ASSAULT` = 3, `bModeQuest = false` |
| `user` param | neighbour uid | quest uid | target uid |
| `map` param | `"0"` | `""` (omitted) | target's map index |
| `privateState` param | not sent | not sent | `1` sent (only when *not* quest) |
| Detection | `gameMode == GAME_MODE_NEIGHBOUR` | `idsUsersQuest.indexOf(uid) >= 0` → `bModeQuest = true`, `mapEntering = "QUEST"` (`core/Base.as:6892-6899`) | `gameMode == GAME_MODE_ASSAULT` and not quest |
| Post-load handling | `Base.Gui.setNeighborStats(payload)` (`core/Base.as:7180`) | `Base.Gui.setAssaultStats(playerInfo, map)` (`core/Base.as:7184`) | same + `Assault.setDefensiveStrategy(privateState.strategy)` (`core/Base.as:7187`) |

**How the client distinguishes a quest map from a PvP map:** purely by the
`idsUsersQuest` whitelist — an array of 90 hard-coded uids
`"100000001" … "100000050"`, `"100000100"`, `"100000500" … "100000550"`
(`core/Base.as:844-845`). `idsNPC = ["100000030","100000031","100000032"]`
(`core/Base.as:846`) marks the "General Mike" NPCs.

The same whitelist also identifies the *player itself* when the player is a test/editor
account (`core/Base.as:1489-1492` → `bModeEditor = true`).

`mapEntering` / `mapLeaving` markers (purely client-side analytics strings):
`"NORM"`, `"NEIGH"`, `"QUEST"`, `"ASSA"` (`core/Base.as:6800-6821`, `core/Base.as:6850-6899`).

### 8.3 Map item → iso element

`processMap` (`core/Base.as:6216-6473`) decodes each `map.items[id]` tuple (§3.5),
resolves the static item via `Base.Items.items.getItem(id)` → `StaticData`, computes
the footprint (rotated by `frame % 2`, `core/Base.as:6372-6381`), detects
out-of-bounds tiles (`0..99` in both axes) and collisions, and pushes the item into
`this.loadedMap`. In assault mode, `PLAYER_SELF` and `PLAYER_ENEMY` are swapped
(`core/Base.as:6338-6352`).

---

## 9. FlashVars contract

Every flashvar is read from `stage.loaderInfo.parameters`.
The full list, with the code that consumes it:

| Flashvar | Type | Read at | Effect |
|---|---|---|---|
| `staticUrl` | String | `core/Base.as:865-868` | → `Base.Main.apfx`, the static asset root (sprites, sounds, fonts, thumbs, images, magic, fx, characters). |
| `dynamicUrl` | String | `core/Base.as:1124-1128` | → `Base.Commands.serverUrl`; **also the switch that enables the game** (`canStart = true`). |
| `language` | String | `core/Base.as:869-877` | → `Base.Main.localization` (lower-cased). Default `"en"`. Also sent as `&language=` on every request and used for font/locale selection. |
| `getText` | String | `core/Base.as:878-885` | Path of the gettext `.mo` catalogue. If absent, the client tries the dev URL `http://dynamic.flash1.dev.socialpoint.es/appsfb/socialwarsdev/locale/` and the base `../locale/` (`core/Language.as:53-68`). |
| `fb_sig_user` | String | `core/Base.as:1086-1093` | → `Base.Commands.phpsessid` = the session/player id. **If absent, debug mode is enabled** (`Base.Commands.debug = true`). |
| `user_key` | String | `core/Base.as:1094-1097` | → `Base.Commands.userKey`; sent as `&user_key=`. |
| `accessToken` | String | `managers/PlayerStatus.as:306` | → `Base.Player.accessToken`; embedded in every `command.php` body. |
| `userCountry` | String | `managers/PlayerStatus.as:304-305` | → `Base.Player.country` (default `"us"`); used for the alliance search and the flag image. |
| `sex` | String | `core/Base.as:982-989` | `"m"` / `"w"`; default `Constants.GENDER_MALE`. |
| `hasSex` | String | `core/Base.as:990-997` | `"0"` ⇒ `sexDefined = false` ⇒ the "choose gender" popup is shown first (→ `set_sex_player.php`). |
| `push_time` | String→int | `core/Base.as:998-1013` | Command flush period in seconds, clamped to 3..60; default 6. |
| `abAttackersDestroy` | String→int | `core/Base.as:1014-1017` | `ABAttackersDestroyBuildings` A/B flag. |
| `alliances` | String→int | `core/Base.as:1018-1021` | `1` ⇒ `AllianceInfo.ENABLED = true`. |
| `abTimerQuests` | String→int | `core/Base.as:1022-1025` | A/B flag. |
| `abTimerAttacks` | String→int | `core/Base.as:1026-1029` | A/B flag (inverted: `1 → 0`, else `1`). |
| `abVisitGeneral` | String→int | `core/Base.as:1030-1033` | A/B flag; also forces `exp_required = 44` for level 2 (`managers/GameDataManager.as:102-105`). |
| `offer_type` | String | `core/Base.as:1034-1037` | → `Base.Main.offerType` (default `"0"`). |
| `friendsInfo` | JSON String | `core/Base.as:1038-1045` | Array of `{uid, pic_square, ...}`; parsed and indexed by `uid` → used for neighbour avatars. |
| `fb_sig_friends` | String | `core/Base.as:1046-1049` | `unescape`d comma-separated list of friend uids → `getAllFriends()` → sent as the `neighbors` param of `get_player_info.php`. |
| `bookmarked` | String | `core/Base.as:1050-1057` | Whether the user bookmarked the app. |
| `like` | String | `core/Base.as:1058-1065` | Whether the user liked the app. |
| `lastInviteSent` | String→uint | `core/Base.as:1066-1073` | Invite cooldown. |
| `lastLoggedIn` | String→uint | `core/Base.as:1074-1081` | → `Base.Main.lastLoggedIn`; used by `secondsSinceLastLogIn()`. |
| `dailyBonus` | String→int | `core/Base.as:1082-1085` | → `Base.Main.consecutiveDays` (daily bonus streak). |
| `sp_ref_cat` | String | `core/Base.as:1141-1144` | → `Base.Main.spRefCat`; install/attribution category. Also appended by the client as `?sp_ref_cat=flash_sync_error` when reloading after a sync error. |
| `canvasaddress` | String | `core/Base.as:1145-1148` | → `Base.Main.canvasAddress`; the URL the browser is sent to when a sync error occurs. |
| `daysSinceRegistration` | String→int | `core/Base.as:1149-1156` | → `Base.Main.daysSinceRegistration` (default 1). |
| `timeZone` | String→int | `core/Base.as:1157-1164` | → `Base.Main.timeZoneModifier` (hours offset used for daily/weekly bonus boundaries). |
| `offerBuilding` | String (csv) | `core/Base.as:1166-1173` | → `Base.Main.offerBuildings` (special offer building ids). |
| `offerBuildingTracking` | String (csv) | `core/Base.as:1174-1177` | → `Base.Main.offerBuildingTrackings`. |
| `debugResources` | String | `core/Base.as:1137-1140` | `"1"` ⇒ every command carries the full `resources` map. |
| `showInitialInvite` | String | `core/Base.as:1129-1132` | `"1"` ⇒ show the invite popup on start. |
| `showInitialGift` | String | `core/Base.as:1133-1136` | `"1"` ⇒ show the gift popup on start. |
| `publishActions` | String→int | `core/Base.as:1182-1185` | `"1"` ⇒ `publishActions` in the command body is `"1"` (Open Graph). |
| `fb_promo_uri` | String | `core/Base.as:1186-1189` | → `Config.FB_PROMO_URI`. |
| `gamecross` | String (csv) | `core/Base.as:1190-1193` | → `Base.Main.spawnGameCross` (cross-promotion game ids). |
| `allowCrossDragons` | String→int | `core/Base.as:1194-1197` | → `Base.Main._allowCrossDragons`. |
| `serverTime` | String→int | `core/Base.as:1556-1561` | Forces `lastServerTimestamp` (and `bForcedServerTime = true`) instead of using the server response timestamp. |
| `game_status` | String | `core/Base.as:7942-7945` | The last telemetry status, used by `statusGreaterThan()` to avoid duplicate `track_game_status.php` posts. |
| `install_id` | String | `core/Base.as:7962-7966` | → `installId` in `track_game_status.php`. |
| `skiphash12341` | any | `core/Base.as:1355,1452,7142` | Disables all server-response HMAC verification. |
| `ownueg…` (any name **longer than 6 chars** whose **first 6 chars are `ownueg`**) | any | `core/Base.as:1098-1107` | Enables debug mode and sets the name of the extra query parameter appended to every request. See §10.3. |
| `spdebug` | any | **not read by this SWF** | Passed by `templates/play.html:88` but no code reads it. **UNVERIFIED** — probably a legacy flag. |
| `forceSyncError`, `forceAttackReload`, `forceQuestReload` | any | **not read by this SWF** | Passed by `templates/play.html:101-103` but unused. **UNVERIFIED** — probably leftovers from a different build. |
| `brk` | any | **not read by this SWF** | A line-break marker used by `templates/play.html` to keep the flashvars string readable. |

### 9.1 Values actually passed by the preservation server

`<upstream-repo>\templates\play.html:88-103`:

```
spdebug=notnull
staticUrl={{ public_url }}/static/socialwars/
dynamicUrl={{ public_url }}/dynamic/menvswomen/srvsexwars/
skiphash12341=notnull
fb_sig_user={{save_info.userid}}
user_key=123456789
language=en
accessToken=AAABbZAm0wdMUBALsOrR0Ho68CLjaOT8SV3vftKg9mbo1zZColaW5FljRVaLxPGxXXnm1M98mTZCAttcQ4GHwvSyXfsyxYmvKMH8Hmn5iliSPnjvIsZA6
sex=m
lastLoggedIn=1349266517
dailyBonus=0
friendsInfo={{friendsInfo | tojson}}
serverTime={{serverTime}}
forceSyncError=1
forceAttackReload=0
forceQuestReload=0
```

Note: `accessToken` and `user_key` are **hard-coded constants** in the template, and
`user_key=123456789` is a fixed literal. `spdebug`, `forceSyncError`,
`forceAttackReload`, `forceQuestReload` are inert for this SWF.

---

## 10. Cross-domain / sandbox / install tracking

### 10.1 Cross-domain policy files

* `utils/SecureImageLoader.as:49-51` sets `LoaderContext.checkPolicyFile = true`
  before loading a remote image (Facebook avatars via `core/GameStatic.as:427`).
* On `Event.COMPLETE`, if `contentLoaderInfo.childAllowsParent` is false, the client
  explicitly fetches the policy file: `Utils.loadPolicyProfileOfUrl(url)`
  (`utils/SecureImageLoader.as:63-76`).
* `core/Utils.as:374-383` → `Security.loadPolicyFile("<scheme>://<host>/crossdomain.xml")`
  (`core/Utils.as:385-396`).
* ⇒ **The server must expose `GET /crossdomain.xml` at the root of the dynamic host**
  (and at the static host, since assets are loaded from a different origin than the
  page). The preservation server serves exactly that
  (`server.py:110-112`, `stub/crossdomain.xml`):

```xml
<?xml version="1.0"?>
<cross-domain-policy>
   <site-control permitted-cross-domain-policies="all"/>
   <allow-access-from domain="*"/>
   <allow-http-request-headers-from domain="*" headers="*"/>
</cross-domain-policy>
```

  The `allow-http-request-headers-from headers="*"` clause matters: it is what allows
  the `X-Requested-With`-style headers some FB SDKs add.
* Cross-origin **SWF** loading uses `LoaderContext(false, ApplicationDomain.currentDomain)`
  — i.e. no sandbox, and the *same* application domain, so cross-SWF scripting is
  allowed (`core/Base.as:7305`, `core/AssetLoader.as:83`, `core/ImageLoader.as:54`).
* `flash.net.LocalConnection` is used for inter-SWF messaging over the channel
  `"myConnection"` (`core/Base.as:8029-8038`, `core/Base.as:8048-8056`).

### 10.2 Same-origin requirement for the API

All dynamic calls go to `dynamicUrl`, which in the preservation deployment is the
**same host** as the page (`server.py:61` → `/dynamic/menvswomen/srvsexwars`).
In the original Zynga deployment the API was on a different host
(`dynamicmw.socialpointgames.com`), hence the crossdomain requirement.

### 10.3 The `ownueg` debug token

`core/Base.as:1098-1107`:

```as3
for(key in this.getStage().loaderInfo.parameters)
{
   if(key.length > 6 && key.substr(0,1) == "o" && key.substr(4,1) == "n"
      && key.substr(2,1) == "u" && key.substr(3,1) == "e"
      && key.substr(1,1) == "w" && key.substr(5,1) == "g")
   {
      Base.Commands.debug = true;
      Base.Commands.weirdSecurity = key;
      f = true;
   }
}
```

The six `substr` constraints pin the **first six characters** of the flashvar name to
`o`,`w`,`n`,`u`,`e`,`g` — in that order — i.e. the name must **start with `ownueg`** —
and `key.length > 6` additionally requires the name to be **at least 7 characters long**
(a bare `ownueg` therefore does *not* match). The whole key is stored as
`CommandManager.weirdSecurity` and appended to every dynamic URL as
`&<key>=1` (`managers/CommandManager.as:596-599` and `managers/CommandManager.as:617-620`).

Side note: when the `fb_sig_user` flashvar is absent the client sets
`Base.Commands.debug = true` but leaves `weirdSecurity` empty
(`core/Base.as:1090-1093`), which would make `getURLWithUserID` emit a bare `&=1`
(`managers/CommandManager.as:596-599`) — a latent bug in the original client.

If no such flashvar is present **and** no `dynamicUrl` flashvar is present, the client
fetches the relative URL `externalized/weird.txt` and uses the part of the file
**before the literal `"SEC"`** as the parameter name
(`core/Base.as:1108-1123`):

```as3
_loc2_ = param1.target.data;
_loc2_ = _loc2_.split("SEC")[0];
Base.Commands.weirdSecurity = _loc2_;
```

So the original deployment could hide the debug parameter name in a static text file
(`externalized/weird.txt`, e.g. containing `xyzSEC123` ⇒ parameter `xyz`).
The preservation server does **not** implement `externalized/weird.txt`
(its `static_assets_loader` would 404 it), but the branch is skipped because
`dynamicUrl` is always supplied by `templates/play.html`.

### 10.4 `sp_ref_cat` / `sp_ref_uid` install tracking

| Field | Where | Notes |
|---|---|---|
| `sp_ref_cat` (flashvar) | `core/Base.as:1141-1144` | → `Base.Main.spRefCat` (String, default `""`). It is the **attribution category** of the install (which campaign/partner brought the player in). |
| `sp_ref_cat` (query) | `managers/CommandManager.as:57,568` | The client appends `?sp_ref_cat=flash_sync_error` to `canvasAddress` when it force-reloads the page after a sync error. The preservation server handles exactly this in `/null` (`server.py:299-311`) and also knows `flash_reload_quest` and `flash_reload_attack`. |
| `sp_ref_uid` | `playerInfo.sp_ref_uid` in the save format | The **install uid** (a numeric install campaign id). Present in the preservation save files (`villages/initial.json:16` → `1000`) but **not read anywhere in this SWF** — it is server-side bookkeeping carried inside `playerInfo`. |
| `sp_ref_cat_install` | `playerInfo.sp_ref_cat_install` | The install category string (`"ts"` in the save files). Also **not read by the SWF**. |
| `install_id` (flashvar) | `core/Base.as:7962-7971` | → `installId` in the `track_game_status.php` body. This is the only install identifier actually transmitted by the client. |

**`UNVERIFIED`:** the original Zynga server's exact semantics for `sp_ref_uid` /
`sp_ref_cat_install` — the SWF never reads them, so the only evidence is their presence
in the `playerInfo` payload (and in the preserved save files, which were probably
captured from the original server's response).

---

## 11. Original vs. preservation server — API surface gaps

The local preservation server (`<upstream-repo>\server.py`)
implements a **subset** of the original API. The following are the gaps, all derived
from the client:

| Endpoint | Client evidence | Local server | Note |
|---|---|---|---|
| `command.php` | `managers/CommandManager.as:386` | ✅ `server.py:313-329` | Hash is **not** verified (see §6.2). |
| `get_game_config.php` | `core/Base.as:1337` | ✅ `server.py:156-164` | Serves `config/main.json` **without** the `<hash>;` prefix; works because `skiphash12341` is set. |
| `get_player_info.php` | `core/Base.as:1416`, `core/Base.as:6990` | ✅ `server.py:166-193` | Distinguishes own / neighbour / quest map via the `user` and `map` params. |
| `sync_error_track.php` | `managers/CommandManager.as:529` | ✅ `server.py:290-297` | |
| `track_game_status.php` | `core/Base.as:7967` | ✅ `server.py:146-154` | |
| `alliance/?method=*` (11 methods) | `core/Config.as:42-60` | ⚠️ catch-all `server.py:333-341` returning `{}` | The catch-all matches any `method`; it does not implement the actual alliance semantics (the client would still show an error because `success` is absent → `handler(_loc5_["data"])` → `undefined`). |
| `bets/get_bets_list.php`, `bets/get_bet_detail.php`, `bets/set_bet.php` | `data/MarketplaceInfo.as:92` etc. | ❌ commented out (`server.py:197-288`) | Fully-implemented reference code exists in the commented block and in `auctions.py` — the shape (`{"result":"success","data":{"bets":[...]}}`) is the canonical one. |
| `set_sex_player.php` | `core/Base.as:1317,1326` | ❌ | Only triggered when `hasSex=0`. |
| `report_error_init.php` | `core/Base.as:1671` | ❌ | Only sent when `Capabilities.isDebugger` (i.e. never in a release player). |
| `get_public_player_info.php` | `popups/PopupPlayerProfile.as:84` | ❌ | GET; shows the "player profile" popup. |
| `get_user_world.php` | `popups/PopupAttackFinished.as:543` | ❌ | GET; resolves a FB uid to a world id. |
| `get_continent_ranking.php` | `newTowns/ExplorationsManager.as:286` | ❌ | GET; the "islands/continents" ranking screen. |
| `get_continent.php` | `core/Config.as:26` (unused) | ❌ | Dead constant — likely the continent list (a sibling of `get_continent_ranking.php`). |
| `clean_assaults.php` | `core/Config.as:34` (unused) | ❌ | Dead constant — likely prunes stale assault records. |
| `register_found_item.php` | `core/Config.as:24` (unused) | ❌ | Dead constant — likely registers a "found item" collectible. |
| `externalized/weird.txt` | `core/Base.as:1112` | ❌ | Only fetched when neither `dynamicUrl` nor an `ownueg` flashvar is present. |
| `/crossdomain.xml` | `core/Utils.as:382` | ✅ `server.py:110-112` | |
| `?sp_ref_cat=flash_sync_error` redirect target | `managers/CommandManager.as:568` | ✅ `server.py:299-311` | |

Additionally, the original API surfaces these behaviours that the local server only
partially reproduces:

1. **Server-side hash verification** of the `data` envelope (§6.2) — the original
   server almost certainly rejected packets with a bad HMAC (the client has a
   dedicated `ERROR_CLIENT_HASH` / `error:"hash"` path, `managers/CommandManager.as:445-448`).
2. **`first_number` gap detection** — the client increments it monotonically per
   command, which only makes sense if the server used it to detect lost/duplicated
   packets.
3. **`tries`** — an attempt counter, meant for server-side de-duplication of retried
   packets (the client re-sends the *same* `first_number` and command list).
4. **`ts` anti-time-hack** — the server compares `ts` with its own clock; the
   `error:"timehack"` path exists (`managers/CommandManager.as:458-464`).
5. **`client_id` session binding** — the server ties `client_id` to the session and
   answers `error:"client_id"` (session stolen) or `error:"no_client_id"`
   (server lost the session) (`managers/CommandManager.as:437-444`).
6. **`user_key` validation** — `error:"user_key"` (`managers/CommandManager.as:449-452`).
7. **`flashVersion` gate** — `error:"bad_flash_version"` forces a client reload
   (`managers/CommandManager.as:465-468`, `core/Base.as:560-562`).
8. **`accessToken`** — carried in the command body so the server could publish
   Open-Graph actions (`managers/CommandManager.as:396`,
   `core/Base.as:1182-1185`).
9. **`publishActions`** — an explicit opt-in for OG publishing.
10. **The 20-command `flash_debug` probe** — the client injects a `flash_debug`
    command every 20 commands for players ≥ level 10
    (`managers/CommandManager.as:158-161`), which the original server used as a
    **anti-cheat / consistency probe** (it echoes the client's own resource totals).
    The preservation server ignores `flash_debug`.

---

## 12. Appendix — class-by-class role summary

| File | Networking role |
|---|---|
| `managers/ServiceManager.as` | Generic JSON-over-HTTP service caller (`callService`), hash-framed body, `success`/`data` unwrapping. |
| `managers/services/Service.as` | Tiny value holder: `service`, `handler`, `ioErrorHander`, `vars` — one instance per in-flight request, keyed by the `URLLoader`. |
| `managers/CommandManager.as` | Command queue, batching, `command.php` framing, retries, error taxonomy, URL building, `sync_error_track.php`. |
| `core/CommandPacket.as` | Value holder: `firstNumber`, `commands`, `loader`, `timestamp`, `tries`, `ioError`. |
| `core/Crypto.as` | HMAC-SHA256 + `<hash>;<payload>` framing + hash verification. |
| `core/Token.as` | **Not networking** — this is the in-game floating resource pickup (gold/steel/oil/wood/XP) rendered on the map. It has nothing to do with auth tokens. |
| `core/Key.as` | **Not networking** — keyboard input handling only (plus the hidden debug key-sequences `arDebug`, `arKC`, `arBM`). |
| `core/Config.as` | Endpoint table, `SERVER_KEY`, `VERSION`, server roots, gameplay tunables. |
| `core/StaticData.as` | Parses `items[]` from the game config. |
| `core/DynamicData.as` | Parses per-item dynamic state. |
| `core/GameStatic.as` | Helpers; the only network-ish call is `loadPhoto()` (Facebook avatar via `SecureImageLoader`). |
| `core/utils/SecureImageLoader.as` | Loads remote images with `checkPolicyFile = true`; triggers the explicit `crossdomain.xml` fetch. |
| `core/Language.as` | Loads the gettext `.mo` catalogue from `getText` flashvar / `../locale/`. |
| `core/AssetLoader.as` | Generic queued asset loader with 1 concurrent request and up to 3 retries, rooted at `apfx`. |
| `managers/GameDataManager.as` | Applies the game-config sections (§3.2). |
| `managers/PlayerStatus.as` | Applies the player-info sections (§3.3); owns `accessToken` and `country`. |
| `core/Base.as` | The orchestrator: flashvar parsing, config load, player-info load, map load, telemetry, asset loading. |

> Note: the requested file `scripts/core/utils/SecureImageLoader.as` does **not** exist;
> the class is at `scripts/utils/SecureImageLoader.as` (package `utils`).
