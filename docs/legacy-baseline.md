# Legacy environment baseline

This document records the legacy Social Wars environment at the preservation
baseline. It is a historical reproduction guide, not a supported modern-runtime
configuration. The Flash-era components described here must remain archival and
must not become dependencies of the future Godot client.

## Evidence status

- **Repository evidence** means a value or behavior is present in the
  `legacy-baseline` tree.
- **Upstream release evidence** means it was observed in the published upstream
  0.02a release metadata or ZIP central directory, not inferred from this source
  checkout.
- **Not yet runtime-verified** means the procedure or compatibility claim has not
  been executed successfully in the current environment.

Static inspection is evidence of source structure; it is not evidence that the
server or game ran successfully.

## Preserved revision and release

| Item | Recorded value | Evidence |
| --- | --- | --- |
| Local baseline | lightweight tag `legacy-baseline` | Repository evidence |
| Baseline commit | `e8c98a03c902eba70323538dc5d4eaba2f2927a1` | Repository evidence; `git rev-parse refs/tags/legacy-baseline^{commit}` |
| Server display/version code | `alpha 0.02` / `0.02a` | Repository evidence: [`version.py`](../version.py#L3-L4) |
| Upstream release | `0.02a`, published 2024-01-27 | Upstream release evidence: [GitHub release](https://github.com/AcidCaos/socialwarriors/releases/tag/0.02a) |
| Upstream archive | `social-warriors_0.02a.zip` | Upstream release evidence: [release asset](https://github.com/AcidCaos/socialwarriors/releases/download/0.02a/social-warriors_0.02a.zip) |
| Packaged Python provenance | ZIP entry `social-warriors_0.02a/python39.dll` | Upstream release evidence; this establishes the bundled interpreter family only |
| Default Flash client | `Basesec_1.5.4.swf` loaded through `SWLoader.swf` | Repository evidence: [`server.py`](../server.py#L91-L95), [`templates/play.html`](../templates/play.html#L82-L103) |
| Default save format version | newly created saves migrate to `0.02a` | Repository evidence: [`sessions.py`](../sessions.py#L110-L127), [`version.py`](../version.py#L8-L49) |

Python 3.9 is therefore known bundle provenance, **not** a verified supported
version range for running the source checkout. No `EXT_VERSION` or equivalent
content-version literal exists in the baseline application files; the explicit
identifiers available are release/server code `0.02a`, save version `0.02a`, and
Flash client `1.5.4`.

### Asset and content identity

The baseline tag and full commit are the only complete identity for the archived
`assets/`, `config/`, and `villages/` trees. Version-labeled files under
`assets/flash/` span `Basesec_1.4.5.swf` through `Basesec_1.5.4.swf` (with gaps),
alongside `Debug_1.5.4.swf` and the unversioned `SWLoader.swf`; only
`Basesec_1.5.4.swf` is selectable in the login template
([`templates/login.html`](../templates/login.html#L40-L51)). `config/main.json`
contains no application/content version field. An asset hash manifest has not
yet been created, so filenames and the baseline commit must not be mistaken for
per-asset integrity verification.

## Python and dependency evidence

The source dependency manifest, [`requirements.txt`](../requirements.txt),
contains only an unpinned `flask` requirement. Source imports additionally require
`requests` in [`server.py`](../server.py#L1-L6) and `jsonpatch` in
[`get_game_config.py`](../get_game_config.py#L1-L9), but neither is declared in
the manifest. The Windows build scripts invoke PyInstaller without declaring or
pinning it: [`build/build.bat`](../build/build.bat#L17-L35) and
[`build/launcher_build.bat`](../build/launcher_build.bat#L14-L30).

No dependency versions are locked. Selecting versions, completing the manifest,
and proving a supported source-Python range belong to the later dependency-lock
change.

## Operating-system evidence

- The packaged flow is documented for Windows in the [README](../README.md#how-to-install-on-windows),
  and the build tooling is Windows batch/PyInstaller tooling.
- The source contains console-title branches for Windows and non-Windows hosts in
  [`server.py`](../server.py#L8-L13).
- The historical [Linux instructions](../LINUX.md) require running the server
  from source and describe a specific Chromium/PPAPI Flash setup. Those
  instructions are repository evidence, not a successful current-host test.
- Flash Player and Flash-capable browser references in [FLASH.md](../FLASH.md)
  are preservation-only. Obsolete Flash/browser combinations should be isolated
  from ordinary browsing and must not be shipped with the modern client.

## Directory and write expectations

Run source commands from the repository root. [`bundle.py`](../bundle.py#L4-L23)
resolves source assets, templates, villages, quests, and configuration from `.`;
it also resolves writable `mods/`, `saves/`, and `auctions/` paths relative to
the process working directory. In a PyInstaller build, bundled read-only data is
resolved below `sys._MEIPASS`, while those writable paths remain next to the
working directory.

At startup, [`sessions.load_saves`](../sessions.py#L34-L68) creates `saves/` if
it is absent and exits if the path cannot be created or is not a directory. The
process therefore needs write access to its working directory and later writes
`saves/<USERID>.save.json` directly ([`sessions.save_session`](../sessions.py#L248-L255)).
The `saves/` directory is intentionally ignored by Git and no player save is
tracked at the baseline; `villages/` contains templates and static villages, not
the mutable player-save directory.

## Startup procedures

### Source checkout (not yet runtime-verified)

The repository-intended entry point is:

```text
python server.py
```

Before that can be called a clean-machine reproduction, a runnable Python must be
installed and the complete dependencies must be selected and installed. The
current Windows host exposes only non-runnable Microsoft Store aliases for
`python` and `python3` (both returned exit code 9009 on 2026-09-13), has no `py`
launcher, and therefore could not execute the entry point. No server/client
startup success is claimed here.

### Published Windows bundle (historical, not currently executed)

The repository instructions say to download and extract the 0.02a bundle, run
the `social-warriors` executable, then open `http://127.0.0.1:5055/` in a
Flash-capable browser. The upstream ZIP central directory names the executable
`social-warriors_0.02a/social-warriors_0.02a.exe`. This packaged procedure was
not executed on the current host.

## Network roots and bootstrap flow

The Flask server binds only `127.0.0.1` on TCP port `5055`
([`server.py`](../server.py#L40-L43)). Its important roots are:

| URL/path | Role |
| --- | --- |
| `http://127.0.0.1:5055/` | Login/save selection; POST stores `USERID` and `GAMEVERSION` |
| `/new.html` | Creates a player save and selects `Basesec_1.5.4.swf` |
| `/play.html` | Renders the Flash embed after validating the session and save |
| `/static/socialwars/` | Local archived assets, including `flash/SWLoader.swf` |
| `/dynamic/menvswomen/srvsexwars/` | Legacy dynamic endpoint root |
| `/dynamic/menvswomen/srvsexwars/get_game_config.php` | Game configuration |
| `/dynamic/menvswomen/srvsexwars/get_player_info.php` | Player or neighbor state |
| `/dynamic/menvswomen/srvsexwars/command.php` | Legacy command submission |
| `/crossdomain.xml` | Flash cross-domain policy |

The bootstrap sequence visible in [`server.py`](../server.py#L56-L99) and
[`templates/play.html`](../templates/play.html#L82-L103) is:

1. `GET /` reloads disk saves and renders either saved-player choices or the
   create-new link.
2. A login POST records the selected `USERID` and `GAMEVERSION`; `/new.html`
   instead creates a new UUID-backed save and selects client `1.5.4`.
3. `/play.html` embeds `SWLoader.swf`, passing the selected Basesec SWF through
   `swftoload`.
4. FlashVars provide the local static and dynamic roots, player ID, language,
   friend data, and server time. The client then calls the PHP-shaped Flask
   compatibility endpoints above.

The offline asset branch is the active code path; the optional GitHub CDN branch
is hard-disabled by `if False` ([`server.py`](../server.py#L116-L129)). No
environment variables are required or read by the baseline application; host,
port, routes, and session secret are source literals.

## Default player and save behavior

[`villages/initial.json`](../villages/initial.json) is the new-player template.
At the baseline it has no player ID or save version, names the empire `Warrior`,
uses map `0`, and begins that map at level `1`, `4` XP, and `2000` each of gold,
wood, oil, and steel. Creation deep-copies the template, assigns a UUID, updates
timestamps, migrates the save to `0.02a`, and writes
`saves/<UUID>.save.json` ([`sessions.new_village`](../sessions.py#L110-L129)).

Existing `saves/` JSON files are loaded at startup and again on `GET /`. Invalid
or corrupt saves are skipped; recognized 0.01a saves receive the migrations in
[`version.py`](../version.py#L8-L49) and are rewritten as 0.02a. This describes
the code path only; representative canonical save fixtures and runtime migration
verification do not yet exist.

## Configuration, patches, and mods

[`get_game_config.py`](../get_game_config.py#L7-L38) loads
`config/main.json`, applies JSON Patch documents, then removes duplicate item
definitions. [`config/patch/patches.txt`](../config/patch/patches.txt) enables,
in order, `atom_fusion_item`, `unit_patch`, `atom_fusion_items_data`,
`atom_fusion_powerup`, and `targets`; the matching `.json` files live beside the
list.

The same loader reads `mods/mods.txt` from the working directory and applies each
uncommented JSON Patch entry in order. At the baseline, the only example,
`no_hiring_needed`, is commented out ([`mods/mods.txt`](../mods/mods.txt)), so no
mod is enabled by default.

## Reproduction status and open inputs

Clean-machine reproduction is **not yet verified**. The immediate blockers are
the incomplete, unpinned dependency manifest; unknown supported source-Python
range; unavailable runnable Python on the current host; and lack of an executed
server-plus-Flash-client smoke test. No automated legacy test, lint, or type-check
command has been verified. The baseline syntax command is documented elsewhere,
but it could not be run without Python and must not be described as a test.

See [Known legacy bugs and limitations](known-legacy-bugs.md) for source-confirmed
stubs, disabled systems, compatibility risks, and explicitly unverified static
findings.
