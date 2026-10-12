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
- **Executed runtime evidence** below records only the exact 2026-09-14 source
  target and checks; it does not retroactively verify the published bundle.

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
version range for running the source checkout. The later evidence below verifies
one exact source target, CPython 3.9.13 on Windows x64. No `EXT_VERSION` or equivalent
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
contains no application/content version field. The generated
[`legacy-manifest.json`](../legacy-manifest.json) records raw Git-blob SHA-256
and sizes for 3,258 baseline files under the nine-extension `legacy-assets-v1`
policy, totaling 758,423,699 bytes. See the
[tool guide](../tools/hash-manifest/README.md) for commands actually executed on
CPython 3.9.13, deterministic generation, independent path/sample checks, and
limitations. This evidence excludes nonmatching extensions, mutable/canonical
player saves, live-worktree and packaged-release bytes, runtime parity, and
asset provenance or rights classification; filenames alone remain insufficient.

## Python and dependency evidence

At the historical baseline, the manifest contained only unpinned `flask` and
omitted unconditional Requests and jsonpatch imports. The current
[`requirements.txt`](../requirements.txt) pins the complete source-runtime graph
for the narrow verified target recorded below. The Windows build scripts invoke
PyInstaller without declaring or pinning it:
[`build/build.bat`](../build/build.bat#L17-L35) and
[`build/launcher_build.bat`](../build/launcher_build.bat#L14-L30).
PyInstaller is build-only; neither it nor a reconstruction of its dependency
graph belongs to this source-runtime lock.

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

### Source checkout (narrow runtime verification)

The repository-intended entry point is:

```text
python server.py
```

Install the exact runtime manifest into an isolated environment first. The
2026-09-13 attempt found only non-runnable Microsoft Store aliases (exit 9009)
and no `py` launcher. On 2026-09-14 an official disposable CPython distribution
was obtained without changing those aliases, PATH, registry installation,
global Python configuration, or Git/authentication settings. Source startup and
root HTTP now have the narrow verification evidence below; client startup does
not.

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
the legacy code path. [Controlled fresh-player fixtures and full-state migration
verification](../tools/save-fixtures/README.md) now capture that bounded path;
authentic early-, mid-, late-game, and stress-town player saves remain unavailable
and unverified. Static neighbor and quest content is not player-save history.

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

Source-runtime dependency installation and loopback root startup are verified
only for the exact environment below. This is not full game or packaged-release
reproduction. No automated gameplay test, lint, or type-check command has been
verified; syntax compilation, package consistency, and HTTP startup are distinct
checks and do not establish behavioral parity.

See [Known legacy bugs and limitations](known-legacy-bugs.md) for source-confirmed
stubs, disabled systems, compatibility risks, and explicitly unverified static
findings.

## Verified source-runtime lock (2026-09-14)

The tested clean source commit is
`fe8904a474af3960f999f080d0f2d2a03b55070f`, exported with `git archive HEAD`
while the worktree was clean. Both installs and startup used that same export
with **only** the candidate `requirements.txt` overlaid. The lock itself is an
uncommitted implementation artifact at verification time, not part of that
commit. Its SHA-256 is
`1f1c19068f7d41e515a1f0fa917c15efa52c00b2f9890feb9b7ef613f1875c61`.
This does not change the separate historical `legacy-baseline` identity above.

### Interpreter provenance and host

- Official Python Software Foundation NuGet distribution `python` version
  `3.9.13`, downloaded as a ZIP-compatible `.nupkg` from
  [the NuGet package](https://www.nuget.org/packages/python/3.9.13), using
  `https://api.nuget.org/v3-flatcontainer/python/3.9.13/python.3.9.13.nupkg`.
  The [CPython Windows guide](https://docs.python.org/3.9/using/windows.html#the-nuget-org-packages)
  identifies this package as the 64-bit CI distribution. Extracting it runs no
  installer and registers no global interpreter.
- Download SHA-256:
  `df29f99c9cf508eda80e878e2795c50ec94431db8d5396a5e455381af593daf4`.
  This is a recorded download fingerprint, not a claim of independent signature
  verification. Package metadata identifies Python Software Foundation and
  CPython commit `6de2ca5`.
- Executed `sys.version`:
  `3.9.13 (tags/v3.9.13:6de2ca5, May 17 2022, 16:36:42) [MSC v.1929 64 bit (AMD64)]`.
  Implementation `cpython`, architecture `AMD64`, pointer size 64 bits.
- Executed `platform.platform()`: `Windows-10-10.0.19045-SP0`;
  `platform.win32_ver()`: `('10', '10.0.19045', 'SP0', 'Multiprocessor Free')`.
- Each fresh venv has `include-system-site-packages = false`. Bootstrap tools
  are pip `22.0.4` and setuptools `58.1.0`, supplied by this interpreter's
  ensurepip. They are recorded separately and are not application runtime pins.

### Import and metadata reconciliation

AST inspection of all 13 tracked Python files and inspection of startup's local
import closure found exactly these external runtime imports:

| Import | Distribution | Reason |
| --- | --- | --- |
| `flask`, `flask.debughelpers` | Flask | `server.py` and `sessions.py`; unconditional private `attach_enctype_error_multidict` import |
| `requests` | requests | Unconditional in `server.py`, even though the remote-asset branch is disabled |
| `jsonpatch` | jsonpatch | Unconditional in `get_game_config.py`; also used by an offline tool |

All other imports in the startup closure are standard-library modules or local
repository modules. Commented Auction House initialization adds no startup
requirements. PyInstaller appears in historical batch packaging scripts, not
in this runtime closure, and its versions/build graph remain unverified.

The installed distribution `Requires-Dist` metadata accounts for all transitives:
Flask requires Werkzeug, Jinja2, itsdangerous, click, and importlib-metadata on
Python <3.10; Werkzeug and Jinja2 require MarkupSafe; click requires colorama on
Windows; importlib-metadata requires zipp. Requests requires charset-normalizer,
idna, urllib3, and certifi. jsonpatch requires jsonpointer. Optional extras
(async, dotenv, socks, documentation, tests, and others) were not requested.
The private helper import was executed successfully under Flask 2.2.5.
Werkzeug 2.2.3 is held within Flask 2.2's API generation; this check establishes
this particular pair, not an exhaustive compatibility matrix or a historical
bundle dependency reconstruction.

Both normalized runtime inventories contain exactly:

```text
certifi==2026.7.22
charset-normalizer==3.5.1
click==8.1.8
colorama==0.4.6
flask==2.2.5
idna==3.19
importlib-metadata==8.7.1
itsdangerous==2.2.0
jinja2==3.1.6
jsonpatch==1.33
jsonpointer==3.0.0
markupsafe==3.0.3
requests==2.32.5
urllib3==2.6.3
werkzeug==2.2.3
zipp==3.23.1
```

### Executed commands and evidence locations

The disposable root for this run is
`C:\Users\Edison\AppData\Local\Temp\socialwars-runtime-740419ee065f46eab323c20a2d601e6b`.
It contains the download, extracted `cpython`, `source.zip`, `source`, two final
fresh environments `verify-one` and `verify-two`, and local evidence. These
paths are transient evidence, not runtime dependencies or a vendored archive.
In these PowerShell commands `$taskRoot` denotes that root and `$runtimePython`
is the indicated environment's `Scripts/python.exe`; no activation or global
configuration is required.

```powershell
curl.exe --fail --location --connect-timeout 15 --max-time 90 https://api.nuget.org/v3-flatcontainer/python/3.9.13/python.3.9.13.nupkg --output (Join-Path $taskRoot 'python-alt.nupkg')
Copy-Item (Join-Path $taskRoot 'python-alt.nupkg') (Join-Path $taskRoot 'python-alt.zip')
Expand-Archive (Join-Path $taskRoot 'python-alt.zip') (Join-Path $taskRoot 'cpython')
& (Join-Path $taskRoot 'cpython/tools/python.exe') -I -c "import sys,platform,struct; print(sys.version); print(sys.implementation); print(platform.platform()); print(platform.machine()); print(struct.calcsize('P')*8)"
& (Join-Path $taskRoot 'cpython/tools/python.exe') -I -c "import platform;print(platform.win32_ver())"
Get-FileHash (Join-Path $taskRoot 'python-alt.nupkg') -Algorithm SHA256
$archivePath = Join-Path $taskRoot 'source.zip'
git archive --format=zip --output=$archivePath HEAD
& (Join-Path $taskRoot 'cpython/tools/python.exe') -I -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" $archivePath (Join-Path $taskRoot 'source')
Copy-Item requirements.txt (Join-Path $taskRoot 'source/requirements.txt')
& (Join-Path $taskRoot 'cpython/tools/python.exe') -I -m venv (Join-Path $taskRoot 'verify-one')
& (Join-Path $taskRoot 'cpython/tools/python.exe') -I -m venv (Join-Path $taskRoot 'verify-two')
```

For **each** final fresh environment, from `source`:

```powershell
& $runtimePython -m pip --isolated install --disable-pip-version-check --no-cache-dir --index-url https://pypi.org/simple -r requirements.txt
& $runtimePython -m pip --isolated check
& $runtimePython -I -c "import importlib.metadata as m,re; print('\n'.join(sorted(re.sub(r'[-_.]+','-',d.metadata['Name']).lower()+'=='+d.version for d in m.distributions() if d.metadata['Name'].lower() not in ('pip','setuptools'))))"
```

Both installs exited 0, both package checks exited 0 with
`No broken requirements found.`, and the sorted inventories matched each other
and all 16 active exact pins. No unpinned runtime distribution or PyInstaller
was installed. These installs used independent no-cache downloads from PyPI.
The disposable logs are `verify-one-install.log`, `verify-two-install.log`,
`verify-one-check.log`, `verify-two-check.log`, and corresponding
`*-inventory.txt`. `metadata.json` records installed dependency metadata;
`imports.json` records inspected imports.

An earlier candidate resolver environment selected the transitive pins. The
initial NuGet v2 download was slow; the flat-container retry succeeded. Their
extraction overlapped accidentally and emitted existing-file errors; the
successful extraction completed before final verification environments were
created. Earlier disposable `env-a`/`env-b` setup also overlapped and one
attempt reported permission denied; these were abandoned and are **not** the
two accepted verification environments. Only newly created `verify-one` and
`verify-two` count as clean-install evidence. No repository source change was
used to resolve these setup issues.

### Contained syntax and root HTTP results

The executed evidence harness was:

```powershell
& (Join-Path $taskRoot 'verify-one/Scripts/python.exe') -I (Join-Path $taskRoot 'verify.py') (Join-Path $taskRoot 'source')
```

`verify.py` uses AST and installed metadata for the inventory assertions above,
checks every active requirement has an exact pin, compares normalized inventories
(excluding pip/setuptools), and verifies the private Flask helper import.
It hashes all existing disposable source files before/after the following checks.
The actual application commands, launched with the locked environment and
`cwd=source`, were:

```text
python -m compileall -q .
python server.py
```

The syntax subprocess returned 0 with empty output. The HTTP subprocess was
launched with `subprocess.Popen([sys.executable, 'server.py'], cwd=root,
stdout=log, stderr=subprocess.STDOUT, env={**os.environ,
'PYTHONUNBUFFERED': '1'})`. A socket probe first asserted that port 5055 was
unoccupied; subsequent probes waited up to ten seconds for loopback readiness
while checking that the launched process stayed alive. The request used
`urllib.request.build_opener(urllib.request.ProxyHandler({})).open(
'http://127.0.0.1:5055/', timeout=10)`, read the response, and asserted status
200 and `<title>Social Wars</title>`. In a `finally` block it called
`process.terminate(); process.wait(timeout=10)` on only that Popen child.
The process PID was `13004`; Windows forced termination returned 1 as expected,
not a startup failure. A final socket probe verified that port 5055 was free.

Recorded HTTP result: **200**, `text/html; charset=utf-8`, **1307 bytes**;
response SHA-256
`e0f7fa2bc4bd6d0587d98427dc2ee85a5d2d454566a68edf0ff1b6697c8d9a28`.
The server log recorded:

```text
 * Serving Flask app 'server'
 * Debug mode: off
 * Running on http://127.0.0.1:5055
127.0.0.1 - - [14/Sep/2026 05:21:50] "GET / HTTP/1.1" 200 -
```

The harness exited 0. Local evidence is `verification.log`, `compileall.log`,
`server.log`, `root-response.html`, and `verify.py` beneath the disposable root.
No existing source file's SHA-256 changed. The only generated files were 13
CPython bytecode files: ten in root `__pycache__`, one in `build/__pycache__`,
and two in `tools/__pycache__`. Startup created `source/saves/` with zero save
files. No browser, Flash Player, SWF, Ruffle, `/play.html`, client bootstrap,
login POST, or game command was executed. Reading archived files for hashes
and syntax inspection did not execute preservation content.

Final worktree inspection showed only `requirements.txt`,
`docs/legacy-baseline.md`, `docs/known-legacy-bugs.md`, and verified setup guidance
in `AGENTS.md` changed. No runtime files were created in the worktree and no
preservation asset, save, or configuration was deleted or overwritten.

### Limits of this verification

This proves two fresh source-runtime installs and one local startup/root HTTP
smoke on this exact host/interpreter, not a clean operating-system VM test,
gameplay parity, save migrations, or a full server-plus-client reproduction.
Other Python 3.9 patches, newer Python, other OS/architectures, packaged builds,
Flash bootstrap, and gameplay paths remain unverified. Python 3.9 and this
older Flask/Werkzeug pair are preservation targets, not a production stack;
no security audit or dependency vulnerability remediation was performed.
Package versions are pinned but wheel hashes are not locked or vendored, so
future package-index availability and artifact integrity are separate concerns.
The interpreter download hash identifies this run's bytes only. Root GET
success does not validate Requests' disabled remote branch or every Flask API.
OpenSpec acceptance, task state, roadmap reconciliation, and Git/PR lifecycle
remain the coordinator's responsibility.

## Server v1 additions (2026-10-12)

Milestone M13 added the first runtime dependency of the authoritative server,
`apps/server-v1/`. This section **adds to** the record above and edits none of
it: the pinned interpreter, the legacy Flask/Werkzeug pair, and every claim in
the sections above are unchanged and remain as recorded.

### Verified interpreter

| Item | Recorded value | Evidence |
| --- | --- | --- |
| Interpreter | pinned CPython **3.9.13**, Windows x64 | Repository evidence; the same executable as every entry above |
| Resolution constraint | `fastapi >=0.129.0` and `uvicorn >=0.40.0` declare `Requires-Python >=3.10` and are unresolvable here | Measured by the resolver, not read from a changelog |
| Ceiling on this interpreter | `fastapi==0.128.8`, `uvicorn==0.39.0` | `<pinned>\python.exe -m pip install -r requirements.txt`, exit 0, and `<pinned>\python.exe -m pip --isolated check` reporting `No broken requirements found.`, exit 0 |

CPython 3.9.13 is therefore the **binding constraint** on the v1 dependency
set, and the pins below are the newest versions pip can install for it. A
different interpreter would resolve a different set; these pins are not a
statement that 0.128.8 is the newest FastAPI.

### Correction to this section's install evidence (2026-10-12)

**The pins above were correct; the evidence for them named an interpreter that
had never been installed into.** The row above now names the pinned
executable explicitly, because the first version of it did not and the claim
was false as written.

What happened, in the order it was found:

1. The section recorded `pip install -r requirements.txt`, exit 0, against
   "this interpreter" - the pinned CPython 3.9.13 at
   `%TEMP%\opencode\cpython39\pkg\tools\python.exe`, which is the executable
   `verify-boot.ps1` selects when `PINNED_PYTHON` is unset.
2. The install had in fact been run against the **PATH** `python`,
   `%LOCALAPPDATA%\Programs\Python\Python39\python.exe`. Same 3.9.13, same
   architecture, **different installation** with its own `Lib\site-packages`.
   Both interpreters satisfy `sys.version == 3.9.13`, so a version check cannot
   tell them apart.
3. **The battery found it, not a check.** The `server-v1-live` phase died with
   `server_exit=1` and no diagnostic in its own output, because the harness
   starts `apps/server-v1/run.py` and captures both of its streams into files
   under `%TEMP%` that it never mentions. The cause was only readable by opening
   `%TEMP%\server-v1-live-phase-err.txt` by hand:
   `ModuleNotFoundError: No module named 'uvicorn'`.
4. Measured on the pinned executable: `flask` 2.2.5 present; **`fastapi`,
   `pydantic`, `uvicorn`, `starlette`, `h11` and `anyio` all absent** - none of
   the twelve, not one.

Corrected by running the install for real on the pinned interpreter. It
resolved exactly the twelve packages at exactly the recorded versions, exit 0,
and `pip --isolated check` reports `No broken requirements found.`, exit 0.
The `apps/server-v1` suite was then re-run **on that interpreter**: `Ran 210
tests`, `OK`, exit 0. Every Server v1 figure in this repository is now a
figure from the pinned executable and not from the PATH alias.

Two changes follow from the cause, not from this one instance:

* `server_v1_live_phase.py` now prints a bounded tail of both service streams,
  with the failed checks, whenever any check fails. A harness whose failure
  mode is "know which temp file to open" is a harness that will be
  misdiagnosed next time.
* **The installed environment is not the repository.** Nothing in Git records
  which interpreter has what installed, so this class of defect can recur for
  any future dependency. It is recorded here rather than treated as closed.

### Pinned versions, exactly as resolved

Direct dependencies added by this change:

| Package | Version | Why it is here |
| --- | --- | --- |
| `fastapi` | 0.128.8 | design D4; the ASGI application and the request typing |
| `pydantic` | 2.12.4 | design D4; the frozen domain models and the intent schemas |
| `uvicorn` | 0.39.0 | **not** named by D4; see the recorded addition below |

Transitives resolved and pinned by the same install:

| Package | Version |
| --- | --- |
| `starlette` | 0.49.3 |
| `anyio` | 4.12.1 |
| `exceptiongroup` | 1.3.1 |
| `annotated-doc` | 0.0.5 |
| `annotated-types` | 0.7.0 |
| `typing-inspection` | 0.4.2 |
| `pydantic-core` | 2.41.5 |
| `h11` | 0.16.0 |

Two transitive requirements were **already** pinned above by earlier work and
are deliberately not duplicated: `anyio` requires `idna>=2.8` and Requests already
pins `idna==3.19`; `uvicorn` requires `click>=7.0` and Flask already pins
`click==8.1.8`.

### Deliberately NOT added: `httpx`

`fastapi.testclient.TestClient` requires `httpx`, so `httpx` would have been the
only **test-only** dependency this repository would have gained. It was not
added. The suite instead calls the ASGI application object directly, in-process,
through `apps/server-v1/tests/asgi_caller.py`. One test module does bind a real
socket (`test_live_server.py`) so that the binding claim is checked against a
socket rather than against an in-process object.

### Deliberately deferred: SQLAlchemy and Alembic

Not installed. design D4 defers persistence migration to M14; `apps/server-v1/`
reads the committed save document through a repository seam
(`server_v1_repository.py`) and has no ORM and no migration tool.

### Verification actually run

| Command | Result |
| --- | --- |
| `python -m pip install -r requirements.txt` | exit **0**, every requirement already satisfied |
| `python -m pip --isolated check` | exit **0**, `No broken requirements found.` |
| `python -B -m unittest discover -s apps/server-v1/tests -p "test_*.py"` | **210 tests**, exit **0** |
| `python -B -c "import fastapi, pydantic, uvicorn"` under 3.9.13 | imports cleanly |

### Why `uvicorn` is here although D4 did not name it

Design D4 adds FastAPI and Pydantic. FastAPI cannot bind a TCP port without an
ASGI server, and this milestone's own task 1.4 requires v1 to bind a port
distinct from 5055 and 5056, so the addition is forced by the tasks rather than
chosen. It is recorded here rather than folded silently into D4.

### Ports

| Surface | Port | Source |
| --- | --- | --- |
| legacy Flask server | 5055 | `server.py:40-43` |
| Compatibility API v0 | 5056 | `apps/compat-api/compat_service.py:937` |
| **Server v1** | **5057** | `apps/server-v1/server_v1_settings.py` |

`assert_port_is_distinct()` raises when 5057 collides with a reserved port, and
`tests/test_settings.py` calls it, so the distinctness is a checked property
rather than a comment. On the verified host `netsh interface ipv4 show
excludedportrange protocol=tcp` reports only 5357, so 5057 is bindable here;
that is a measurement of **this** host and not a guarantee about any other.

### Limits of this verification

This records a package install, a consistency check, an import check, and a
210-test suite run on this exact host and interpreter. It establishes **no**
runtime server start-up beyond the loopback process the suite itself starts and
stops, **no** gameplay behaviour, **no** save migration, and **no** parity with
the Compatibility API beyond the single executed-legacy transaction the parity
test compares. Wheel hashes are still not locked or vendored, exactly as
recorded above, so future package-index availability and artifact integrity
remain a separate concern. `uvicorn` was added here and is **not** part of the
legacy Flask/Werkzeug baseline, which is untouched.
