# Known legacy bugs and limitations

This inventory is tied to the `legacy-baseline` tag at
`e8c98a03c902eba70323538dc5d4eaba2f2927a1`. It distinguishes what the source
explicitly leaves incomplete or disabled from risks inferred by inspection.
Nothing in the “unverified” sections is presented as a reproduced runtime
failure. See the [legacy environment baseline](legacy-baseline.md) for setup and
provenance.

## Evidence classes

- **Source-confirmed incomplete/disabled:** the baseline code contains an
  explicit stub, disabled branch, commented route, or TODO describing missing
  behavior.
- **Compatibility risk:** a dependency, platform, protocol, or security boundary
  may prevent reliable operation or safe exposure; runtime impact has not been
  reproduced here.
- **Unverified static inference:** inspection suggests a defect, but no runnable
  legacy environment was available to exercise the path.

## Source-confirmed incomplete or disabled behavior

| Area | Baseline evidence | Recorded limitation |
| --- | --- | --- |
| Auction House | [`server.py` initialization](../server.py#L27-L29) and [auction routes](../server.py#L182-L275) | Initialization and all three HTTP handlers are commented out, so the module is not exposed by the server. The module itself also leaves round handling as a TODO and ends `set_bet` with `pass` ([`auctions.py`](../auctions.py#L112-L151), [`auctions.py`](../auctions.py#L178-L201)). |
| Alliance endpoint | [`server.py:318`, `alliance`](../server.py#L318-L328) | The endpoint exists only to suppress a client error and always returns an empty object; alliance behavior is not implemented. |
| Save backup | [`sessions.py:244`, `backup_session`](../sessions.py#L242-L246) | The backup function is a TODO/no-op. Normal save writing still occurs separately and should not be mistaken for a backup. |
| Atom Fusion power-up purchase | [`command.py:720`, `buy_powerups`](../command.py#L720-L725) | The handler reads the index, contains only a TODO, and prints a message; it performs no documented power-up state mutation. |
| Attack completion | [`command.py:808`, `end_attack`](../command.py#L808-L884) | **Source-confirmed incomplete:** the handler already JSON-decodes `args[0]` and reads named response fields. Its TODOs are limited to parsing additional data, mutating the victim player's save, and recording attack logs; runtime effects were not verified here. |
| Remote asset fallback | [`server.py:116`, `static_assets_loader`](../server.py#L116-L129) | The GitHub CDN branch is guarded by literal `if False`; only the local/offline asset path is active. |

These are statements about reachable source structure and explicit omissions,
not claims about every player-visible symptom.

## Compatibility and reproducibility risks

| Risk | Baseline evidence | Status |
| --- | --- | --- |
| Incomplete dependency manifest | [`requirements.txt`](../requirements.txt) declares only unpinned `flask`, while [`server.py`](../server.py#L1-L6) imports `requests` and [`get_game_config.py`](../get_game_config.py#L1-L9) imports `jsonpatch`. PyInstaller is invoked only by the build scripts ([`build/build.bat`](../build/build.bat#L17-L35)). | Source-confirmed manifest gap; exact compatible versions remain unverified. |
| Flask-version coupling | [`server.py`](../server.py#L31-L34) imports `attach_enctype_error_multidict` from Flask's internal `flask.debughelpers` module. | Compatibility risk with unpinned Flask releases; no failure was reproduced here. |
| Obsolete Flash/browser runtime | The [Windows/Flash guide](../FLASH.md) and [Linux guide](../LINUX.md) require legacy Flash-capable browser configurations. | Security and platform compatibility risk. Use only in an isolated preservation environment; do not make Flash a modern runtime dependency. |
| Relative writable paths | [`bundle.py`](../bundle.py#L16-L23) defines `mods/`, `saves/`, and `auctions/` relative to `.`, and [`sessions.py`](../sessions.py#L40-L68) creates/reads `saves/`. | Starting from a different working directory or without write permission can change or prevent persistence; not runtime-tested here. |
| Development-only server/session settings | [`server.py`](../server.py#L335-L339) uses Flask's built-in server and a literal session secret while binding to loopback by default. | Suitable only as preserved local behavior; external exposure has not been tested and is not supported by this document. |

## Unverified static inferences

- [`server.py`](../server.py#L300-L316) extracts the first 64 characters of a
  command payload as `data_hash` but does not compare or otherwise use the hash
  before applying commands. Static inspection therefore suggests that command
  integrity is not checked; no forged request was sent to confirm the effect.
- In the hard-disabled remote asset branch,
  [`except requests.exceptions`](../server.py#L119-L127) appears to name a module
  rather than an exception class. That branch was neither enabled nor exercised,
  so no error-handling failure is claimed as reproduced.
- [`sessions.save_session`](../sessions.py#L248-L255) writes JSON directly to the
  destination file, while `backup_session` is a no-op. Static inspection finds no
  temporary-file/replace or backup step; interruption and corruption behavior
  were not tested.

## Runtime verification unavailable

On 2026-09-13, `python` and `python3` resolved only to Microsoft Store app aliases
and each returned exit code 9009; `py` was not installed. Consequently the server,
source startup, save paths, Flask compatibility, Flash bootstrap, and suspected
failures above were not executed. Clean-machine reproduction remains open until
the dependency-lock change supplies pinned dependencies and a runnable
environment, followed by an explicit smoke test.

This document must be updated when a finding is actually reproduced: record the
environment and test evidence, then move it out of the unverified category rather
than silently strengthening the historical claim.
