## Context

See `proposal.md` for motivation. The baseline is fixed by the local lightweight tag `legacy-baseline` at `e8c98a03c902eba70323538dc5d4eaba2f2927a1`. The source manifest declares only unpinned `flask`, while imports also require `requests` and `jsonpatch`; the build scripts additionally invoke PyInstaller. The current host exposes only non-runnable Microsoft Store Python aliases. The upstream 0.02a release is dated 2024-01-27, and its ZIP central directory contains `social-warriors_0.02a/python39.dll`, which is evidence for the packaged runtime but not a verified source-support range.

## Goals / Non-Goals

**Goals:**

- Make every operational or compatibility statement traceable to repository or release evidence.
- Separate intended startup instructions from steps actually executed on the current host.
- Make unresolved reproducibility gaps explicit inputs to the next dependency-lock change.
- Keep player-facing instructions intact while adding a preservation-oriented index.

**Non-Goals:**

- Selecting or pinning dependency versions.
- Installing Python, Flash, browsers, or packages.
- Running or repairing the legacy server/client.
- Cataloging every endpoint or game command.
- Changing or relocating preserved files.

## Decisions

1. **Classify claims by evidence level.** Use “repository evidence” for facts directly visible in the baseline tree, “upstream release evidence” for the published 0.02a archive, and “not yet runtime-verified” for startup or compatibility claims that could not be executed. This is preferred over a single undifferentiated setup guide because it prevents inferred compatibility from becoming false preservation history.

2. **Document Python 3.9 as bundle provenance, not a source constraint.** The `python39.dll` entry establishes what the 0.02a Windows bundle shipped. The source checkout’s supported Python version remains unverified until dependency locking and clean-environment testing. Declaring Python 3.9 as already supported would overstate the evidence.

3. **Separate declared, imported, and build-only dependencies.** Record `flask` as declared, `requests` and `jsonpatch` as imported but undeclared, and PyInstaller as build-only usage. Do not invent versions. The following M0 dependency-lock change owns version selection and installation verification.

4. **Separate baseline operation from limitations.** Put reproducibility inputs and startup flow in `docs/legacy-baseline.md`; put bugs, stubs, disabled systems, and compatibility risks in `docs/known-legacy-bugs.md`. Cross-link them and add both to the README so facts remain discoverable without bloating the player instructions.

5. **Preserve legacy Flash instructions with an explicit safety/runtime boundary.** Record Flash-era requirements as historical reproduction instructions only. Do not recommend bundling them into the future modern client or imply they are safe for general browsing.

## Risks / Trade-offs

- **Historical release evidence may not define source compatibility** → Label Python 3.9 and packaged components narrowly and defer support claims to verified dependency locking.
- **Static source review may misclassify a suspected failure as reproduced** → Separate source-confirmed incomplete behavior from runtime-observed failures and say when execution was unavailable.
- **Documentation can drift as M0 progresses** → Include baseline tag/commit provenance and require later changes to update verification status rather than rewriting historical evidence.
- **Flash reproduction guidance exposes obsolete-runtime risk** → Keep it preservation-only, retain existing archival references, and warn against ordinary web use.

## Migration Plan

1. Add the two preservation documents from baseline and upstream-release evidence.
2. Add narrow README links without changing existing installation steps.
3. Verify cited repository paths, versions, URLs, and limitation references statically.
4. Leave clean-machine reproduction marked incomplete; the next dependency-lock change will update verification evidence after a runnable environment exists.
