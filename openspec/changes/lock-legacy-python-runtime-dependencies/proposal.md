## Why

The preserved source checkout cannot currently be reproduced from a clean environment because `requirements.txt` declares only unpinned Flask while startup also requires Requests and jsonpatch. M0 needs one evidence-backed, fully pinned Python 3.9 source-runtime dependency set and an executed clean-environment smoke test before the legacy environment can be called reproducible.

## What Changes

- Replace the incomplete runtime manifest with exact direct and transitive pins that remain installable through `python -m pip install -r requirements.txt`.
- Establish and record one explicitly identified CPython 3.9 patch release as the verified preservation source runtime; Python 3.9 is a historical compatibility target, not the modern application baseline.
- Verify the lock from empty isolated environments, including repeat installation, `pip check`, resolved-version comparison, syntax compilation, server startup, and a loopback HTTP smoke test on port 5055 without executing Flash.
- Record the commands, environment, results, limitations, and any generated working-directory state in the legacy baseline and known-bugs documentation.
- Update repository setup/check instructions only with commands that were actually executed successfully.
- Treat the absence of any compatible dependency set without source changes as a blocker rather than silently changing legacy behavior.

## Capabilities

### New Capabilities

- `legacy-runtime-reproducibility`: Defines the pinned legacy Python source runtime and the evidence required to reproduce and verify it in an isolated clean environment.

### Modified Capabilities

None.

## Impact

The planned implementation affects `requirements.txt`, preservation documentation, verified setup/check instructions, and the root-owned roadmap status. It does not alter application behavior, lock PyInstaller or rebuild the historical executable, execute a Flash client, modernize the backend, create asset hashes or save fixtures, or begin protocol work.
