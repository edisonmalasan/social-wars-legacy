## Why

The recorder, replay, and state-diff tools now provide bounded behavioral evidence, but the repository has no complete endpoint inventory distinguishing active routes, framework defaults, commented-out routes, and stubs. A source-grounded endpoint catalog is the next initial-backlog objective before command cataloging and content normalization.

## What Changes

- Add a reviewed machine-readable endpoint catalog and readable documentation covering the 15 explicit active routes, Flask's implicit static route, and three commented-out auction routes.
- Record declared versus effective HTTP methods, route parameters, required and optional input names, response branches, state/persistence effects, source references, and evidence classification without credential values or gameplay-parity claims.
- Add a read-only offline verifier that checks catalog structure, route coverage and source references against current source without importing or executing the legacy application; reject unsupported route syntax instead of silently dropping it.
- Add focused regression tests for route extraction, drift detection, catalog consistency, and containment.
- Leave all legacy handlers and behavior unchanged; classify the alliance placeholder and disabled auction routes explicitly rather than repairing them.

## Source-grounded endpoint inventory

References below identify declarations in `server.py` at proposal time. `D` expands to `/dynamic/menvswomen/srvsexwars` (`server.py:54`). Omitted methods default to GET; Flask adds HEAD for GET and automatic OPTIONS. These are source observations, not executed gameplay evidence.

| Route | Declared methods | Source | Classification |
| --- | --- | --- | --- |
| `/` | GET, POST | `server.py:58` | Login; clears session, reloads saves, renders or redirects |
| `/play.html` | Default GET | `server.py:77` | Session-gated Flash reference page |
| `/new.html` | Default GET | `server.py:93` | Creates village and changes session; not read-only |
| `/crossdomain.xml` | Default GET | `server.py:99` | Archived policy file serving |
| `/img/<path:path>` | Default GET | `server.py:103` | Template images |
| `/avatars/<path:path>` | Default GET | `server.py:108` | Template avatars |
| `/css/<path:path>` | Default GET | `server.py:112` | Template styles |
| `/static/socialwars/<path:path>` | Default GET | `server.py:118` | Local assets; disabled remote branch at `server.py:121` |
| `D/track_game_status.php` | POST | `server.py:135` | Reads status inputs; empty response |
| `D/get_game_config.php` | Default GET | `server.py:145` | Configuration response |
| `D/get_player_info.php` | POST | `server.py:155` | Player/neighbor/quest branches; player mutation in `get_player_info.py:4` |
| `D/sync_error_track.php` | POST | `server.py:279` | Input-reading acknowledgement |
| `/null` | Default GET | `server.py:288` | Flash diagnostic redirect; unknown category leaves reason unset |
| `D/command.php` | POST | `server.py:302` | Recorded dispatcher transaction and persistence |
| `D/alliance/` | POST | `server.py:326` | Active placeholder; empty object response, not implemented alliances |
| `/static/<path:filename>` | Framework default | `server.py:45` | Implicit Flask static registration, distinct from explicit asset route |
| `D/bets/get_bets_list.php` | Commented POST | `server.py:186` | Disabled; not registered |
| `D/bets/get_bet_detail.php` | Commented POST | `server.py:217` | Disabled; not registered |
| `D/bets/set_bet.php` | Commented POST | `server.py:248` | Disabled; not registered |

The implementation must distinguish these 15 explicit registrations, one implicit registration, and three disabled declarations. It must verify framework defaults against the pinned Flask behavior without importing `server.py`, and must not mistake comments for active routes.

## Capabilities

### New Capabilities

- `endpoint-inventory`: Source-grounded, evidence-labeled inventory of legacy routes with deterministic offline consistency verification.

### Modified Capabilities

None.

## Impact

Adds `docs/legacy-protocol/endpoints.json`, `docs/legacy-protocol/endpoints.md`, and focused tooling/tests under `tools/endpoint-catalog/`; updates documentation links and executed-check references. Uses Python 3.9 standard-library tooling, with no dependency upgrade, server import, network, browser, Flash, save mutation, modern API, command catalog, or gameplay change. M1 normal-gameplay discovery and broad M2 gameplay coverage remain incomplete; this change does not claim those milestone exits.
