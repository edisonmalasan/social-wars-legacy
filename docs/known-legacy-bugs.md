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
  may prevent reliable operation or safe exposure; unverified impacts are
  identified below and narrow dependency/startup verification is recorded separately.
- **Unverified static inference:** inspection suggests a defect, but the affected
  path has not been exercised. Root HTTP startup alone does not verify gameplay.

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
| Historical incomplete dependency manifest | At the baseline, `requirements.txt` declared only unpinned `flask`, while [`server.py`](../server.py#L1-L6) imports `requests` and [`get_game_config.py`](../get_game_config.py#L1-L9) imports `jsonpatch`. PyInstaller is invoked only by the build scripts ([`build/build.bat`](../build/build.bat#L17-L35)). | Historical gap resolved by the current [16-distribution exact source-runtime lock](../requirements.txt); two fresh installs and pip checks passed on Windows x64 CPython 3.9.13. PyInstaller/build reproduction remains unverified. |
| Flask-version coupling | [`server.py`](../server.py#L31-L34) imports `attach_enctype_error_multidict` from Flask's internal `flask.debughelpers` module. | Private helper import and root HTTP startup verified with Flask 2.2.5 / Werkzeug 2.2.3. Other version combinations and Flask-dependent gameplay paths remain unverified. |
| Obsolete Flash/browser runtime | The [Windows/Flash guide](../FLASH.md) and [Linux guide](../LINUX.md) require legacy Flash-capable browser configurations. | Security and platform compatibility risk. Use only in an isolated preservation environment; do not make Flash a modern runtime dependency. |
| Relative writable paths | [`bundle.py`](../bundle.py#L16-L23) defines `mods/`, `saves/`, and `auctions/` relative to `.`, and [`sessions.py`](../sessions.py#L40-L68) creates/reads `saves/`. | Disposable repository-root startup created an empty saves directory; other working directories, permission failures, and player-save persistence remain unverified. |
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

## Narrow runtime verification (2026-09-14)

The 2026-09-13 attempt found only Microsoft Store aliases (exit 9009) and no
`py` launcher. This historical host limitation was bypassed with an extracted
official Python Software Foundation NuGet CPython 3.9.13 AMD64 distribution,
without changing global interpreter configuration. The exact tested clean source
commit was `fe8904a474af3960f999f080d0f2d2a03b55070f`, exported to a disposable
copy with only the candidate lock overlaid; the lock was not yet committed.
The host reported `Windows-10-10.0.19045-SP0`.

Both newly created environments installed all 16 exact runtime pins, passed
`python -m pip --isolated check`, and produced identical normalized inventories.
The private Flask helper import succeeded. In the disposable source copy,
`python -m compileall -q .` exited 0 and `python server.py` returned HTTP 200
from `http://127.0.0.1:5055/`. The harness terminated only its own child and
verified the port was released. Existing source-file hashes were unchanged;
generated state was 13 bytecode files and an empty saves directory, all outside
the worktree. No Flash, SWF, Ruffle, or browser execution occurred.

See [the verified baseline evidence](legacy-baseline.md#verified-source-runtime-lock-2026-09-14)
for exact interpreter/download hashes, dependency inventory, commands, response
fingerprint, logs, setup retries, and limitations. The manifest/startup gap is
resolved for this exact target; no reproduced gameplay defect or security fix
is claimed. Save migrations, client bootstrap, other Python versions/platforms,
and historical packaged builds remain unverified. This older preservation
runtime is not a production recommendation; no security audit was performed.

Update each finding when its affected path is actually reproduced, recording
the environment and evidence rather than strengthening static claims silently.
