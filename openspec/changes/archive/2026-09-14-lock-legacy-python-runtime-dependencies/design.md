## Context

See `proposal.md` for motivation and `specs/legacy-runtime-reproducibility/spec.md` for the behavioral contract. The baseline source has one unpinned Flask declaration, unconditional imports of Requests and jsonpatch, and a private Flask helper import that constrains compatible Flask versions. Historical build scripts invoke PyInstaller, but packaged-build reproduction is distinct from running the source server. The current host exposes no runnable Python command, so Apply must obtain an isolated interpreter before it can select or verify pins.

## Goals / Non-Goals

**Goals:**

- Produce one complete, exact source-runtime dependency graph supported by executed evidence.
- Verify a narrowly defined Windows x64 CPython 3.9 target in disposable environments.
- Preserve the existing installation entry point and legacy application behavior.
- Leave an auditable record that another operator can repeat.

**Non-Goals:**

- Claim support for every Python 3.9 patch, Python 3.10+, Linux, or macOS.
- Lock PyInstaller or reproduce the upstream executable bundle.
- Fix the private Flask import, change server behavior, or modernize dependencies for security.
- Execute the Flash client or expand into later M0 deliverables.

## Decisions

1. **Verify one narrow Python target before considering a version matrix.** Apply will use an exact Windows x64 CPython 3.9 patch release and record how it was obtained. This matches the only preserved interpreter-family and platform provenance while avoiding unsupported claims. A multi-version or cross-platform matrix is deferred until a separate change has evidence and need for it.

2. **Use `requirements.txt` as the complete lock and retain the documented install command.** Direct dependencies and their transitive runtime distributions will each use exact `==` pins, with comments distinguishing why direct packages are required. A separate constraints file or resolver-specific lock would add another installation contract without current tooling support.

3. **Select compatibility from executed evidence, not release recency.** The implementer will determine a candidate graph compatible with the unchanged private Flask import and Python target, install it, inspect the resolved graph, and then verify the final exact pins. If compatibility requires an application code change, Apply stops and reports a blocker instead of broadening this change.

4. **Verify repeatability in two fresh virtual environments.** Both environments will be created from the same interpreter and source revision. Installation, `pip check`, and normalized runtime distribution/version inventories must agree; bootstrap tools that are not application runtime dependencies are recorded separately rather than silently treated as locked application packages.

5. **Run the server smoke test from a disposable source copy.** The copy preserves repository-root relative paths while containing `saves/`, bytecode, logs, and other generated state outside the worktree. The test starts `python server.py`, waits for `127.0.0.1:5055`, requests `/`, captures the result, and terminates only the process it started. It does not open `/play.html` in a browser or execute any Flash content.

6. **Record evidence where operators already look.** `docs/legacy-baseline.md` will hold the verified environment, lock inventory, commands, and results. `docs/known-legacy-bugs.md` will update the manifest and Flask-coupling status without erasing remaining risks. `AGENTS.md` setup/check commands change only when the corresponding commands have actually succeeded.

## Risks / Trade-offs

- **An old Flask-compatible graph may contain known security issues** → Keep the verified server loopback-only and label this as an isolated preservation runtime, not a production stack.
- **Python 3.9 bundle provenance may not match source-runtime behavior** → Require an executed source startup test and make failure blocking.
- **Package indexes or wheels can change availability** → Record exact versions, interpreter details, source revision, and installation commands; artifact vendoring is outside this bounded change.
- **Two environments on one host do not prove cross-platform support** → State the verified platform narrowly and defer a matrix.
- **Startup creates writable state** → Run from a disposable copy and confirm the tracked worktree stays unchanged except for approved dependency and documentation files.

## Migration Plan

1. Obtain the exact isolated CPython 3.9 interpreter and record its provenance without changing repository or global Git/authentication state.
2. Resolve a candidate runtime graph from the known direct imports, then replace the incomplete manifest with exact direct and transitive pins.
3. Install and verify the lock twice in fresh environments, including consistency and normalized inventory comparison.
4. Run syntax compilation and the contained loopback startup smoke test from a disposable source copy.
5. Update preservation and verified-command documentation with actual evidence, inspect the dependency-only diff, and run OpenSpec validation.

Rollback is a normal revert of the dependency/documentation commit; preserved assets, saves, configuration, and application source are unchanged.
