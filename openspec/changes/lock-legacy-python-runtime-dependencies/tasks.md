## 1. Establish the verified runtime target

- [ ] 1.1 Obtain an isolated Windows x64 CPython 3.9 interpreter without changing repository, Git, or authentication configuration; record its source and exact implementation/patch/platform details, and verify them with executed interpreter and platform-version commands.
- [ ] 1.2 Reconcile every unconditional third-party import used by `server.py` startup with package metadata, distinguish direct runtime, transitive runtime, and build-only dependencies, and verify the inventory accounts for Flask, Requests, jsonpatch, the private Flask helper constraint, and PyInstaller's exclusion.

## 2. Create and reproduce the dependency lock

- [ ] 2.1 Replace the incomplete `requirements.txt` with exact `==` pins for the complete compatible source-runtime graph, retaining `python -m pip install -r requirements.txt`; verify every active requirement is exactly pinned, all direct startup dependencies are represented, and build-only PyInstaller is absent.
- [ ] 2.2 Create two fresh isolated environments from the verified interpreter and the same recorded clean source revision, install the lock independently in each, run `python -m pip check`, and compare normalized installed runtime distribution/version inventories; verify both installations and checks succeed and the inventories are identical, or report the change blocked without altering legacy source behavior.

## 3. Verify contained source startup

- [ ] 3.1 Copy the preserved source revision to a disposable verification location, run `python -m compileall -q .` there with the locked environment, and verify the syntax check succeeds while the tracked worktree receives no generated saves, caches, or bytecode.
- [ ] 3.2 Start `python server.py` from the disposable copy's repository root, wait for `127.0.0.1:5055`, request `/`, capture the HTTP result and server log, then stop only the process started by the check; verify the response is successful and no Flash, SWF, Ruffle, or browser runtime executes.

## 4. Record evidence and perform final checks

- [ ] 4.1 Update `docs/legacy-baseline.md` and `docs/known-legacy-bugs.md` with the exact tested source commit, lock, interpreter/host evidence, commands, results, and remaining platform/build/security limitations; update `AGENTS.md` only for commands actually executed successfully, and verify documentation never broadens the tested support claim.
- [ ] 4.2 Inspect the final diff to confirm only the approved dependency manifest, preservation documentation, verified command guidance, OpenSpec task state, and root-owned roadmap status changed; run `git diff --check`, OpenSpec implementation verification available in the installed workflow, and `openspec validate lock-legacy-python-runtime-dependencies --strict`, treating every CRITICAL or WARNING finding as blocking.
