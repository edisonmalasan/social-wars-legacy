# Legacy server endpoint inventory

Source-grounded inventory of the legacy Social Wars Flask server (`server.py`), verified offline by `tools/endpoint-catalog/verify_endpoints.py` against `endpoints.json` in this directory.

- **Evidence status: source inspection only.** No endpoint in this inventory has executed endpoint-level behavioral evidence; the documented contained root GET smoke in `docs/legacy-baseline.md` is the only executed runtime evidence and predates this catalog.
- **Evidence classification**: each entry in `endpoints.json` carries an `evidence` string stating what is source observation and what evidence is unavailable. No entry claims gameplay parity or complete command discovery.
- **Method policy**: omitted methods default to GET; Flask adds HEAD for GET and automatic OPTIONS.
- Dynamic routes are written in full so this inventory stays literally consistent with `endpoints.json`; the dynamic root `/dynamic/menvswomen/srvsexwars` is defined at `server.py:54` and the game static root `/static/socialwars` at `server.py:53`.
- All 19 entries below mirror `endpoints.json`; this document is a readable view, not a separate record.

## Active routes (15 explicit registrations)

| Route | Methods (declared → effective) | Handler | Behavior summary |
| --- | --- | --- | --- |
| `/` | GET, POST → GET, HEAD, OPTIONS, POST | `login` | Clears session, reloads saves; GET renders login, POST sets session and redirects to `/play.html` |
| `/play.html` | default → GET, HEAD, OPTIONS | `play` | Session-gated archival Flash reference page; redirects to `/` when session fields are missing or USERID is unknown |
| `/new.html` | default → GET, HEAD, OPTIONS | `new` | State-changing default GET: creates and persists a village, sets session, redirects to `play.html` |
| `/crossdomain.xml` | default → GET, HEAD, OPTIONS | `crossdomain` | Serves the archived crossdomain policy file |
| `/img/<path:path>` | default → GET, HEAD, OPTIONS | `images` | Template image serving |
| `/avatars/<path:path>` | default → GET, HEAD, OPTIONS | `avatars` | Template avatar serving |
| `/css/<path:path>` | default → GET, HEAD, OPTIONS | `css` | Template style serving |
| `/static/socialwars/<path:path>` | default → GET, HEAD, OPTIONS | `static_assets_loader` | Local asset serving; disabled remote CDN branch behind `if False:` |
| `/dynamic/menvswomen/srvsexwars/track_game_status.php` | POST → OPTIONS, POST | `track_game_status_response` | Reads status/installId/user_id, logs, empty 200 |
| `/dynamic/menvswomen/srvsexwars/get_game_config.php` | default → GET, HEAD, OPTIONS | `get_game_config_response` | Requires USERID/user_key/language; returns dynamic config |
| `/dynamic/menvswomen/srvsexwars/get_player_info.php` | POST → OPTIONS, POST | `get_player_info_response` | Player/neighbor/quest branches; current-player branch mutates login timestamp and resets despite the read-sounding name |
| `/dynamic/menvswomen/srvsexwars/sync_error_track.php` | POST → OPTIONS, POST | `sync_error_track_response` | Reads USERID/user_key/language, empty 200 |
| `/null` | default → GET, HEAD, OPTIONS | `flash_sync_error_response` | Flash diagnostic redirect to `/play.html`; unknown `sp_ref_cat` raises UnboundLocalError (reason unset) |
| `/dynamic/menvswomen/srvsexwars/command.php` | POST → OPTIONS, POST | `command_response` | Recorded dispatcher transaction; executes commands and persists the player save |
| `/dynamic/menvswomen/srvsexwars/alliance/` | POST → OPTIONS, POST | `alliance` | Registered placeholder returning an empty object; **alliance gameplay is not implemented** |

## Framework registration (implicit)

| Route | Methods (declared → effective) | Handler | Behavior summary |
| --- | --- | --- | --- |
| `/static/<path:filename>` | default → GET, HEAD, OPTIONS | `static` (Flask default) | Framework-provided static file serving registered by Flask when `static_folder` is set at `server.py:45`; distinct from the explicit `/static/socialwars/<path:path>` asset route |

## Disabled declarations (commented out, not registered)

| Route | Declared methods | Source | Status |
| --- | --- | --- | --- |
| `/dynamic/menvswomen/srvsexwars/bets/get_bets_list.php` | POST | `server.py:186-215` | Commented out; not registered |
| `/dynamic/menvswomen/srvsexwars/bets/get_bet_detail.php` | POST | `server.py:217-246` | Commented out; not registered |
| `/dynamic/menvswomen/srvsexwars/bets/set_bet.php` | POST | `server.py:248-277` | Commented out; not registered |

The auction routes are disabled declarations: they are not registered, have no runtime path, and the auction house module is also commented out (`server.py:27-29`).

## Notes on evidence

- All behavioral descriptions come from reading `server.py` and the modules it calls; none were executed for this inventory.
- `command.php` has contained replay evidence for four recorded commands in `tools/protocol-replay`; that evidence does not establish progressed-player or general gameplay parity.
- No credentials or private player records appear in this inventory.
