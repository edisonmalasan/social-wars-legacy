## 1. Record the legacy baseline

- [x] 1.1 Create `docs/legacy-baseline.md` with the baseline tag and full commit, evidence-status legend, Python and dependency evidence, supported/observed operating-system paths, source and packaged startup procedures, working-directory and writable-path expectations, host/port and endpoint roots, Flash bootstrap sequence, default player/save behavior, configuration and patch/mod loading, release/content/save/client versions, and explicit clean-machine verification status; verify every repository path and literal value against `legacy-baseline` or the cited upstream 0.02a release evidence.
- [x] 1.2 Create `docs/known-legacy-bugs.md` that classifies source-confirmed incomplete or disabled behavior separately from compatibility risks and unverified static inferences, covers the dependency-manifest gap and unavailable current runtime, and links each code-based finding to a concrete repository path/line or symbol; verify the document makes no unsupported claim that a suspected failure was reproduced.

## 2. Make preservation documentation discoverable

- [x] 2.1 Add concise links for both new documents to the README documentation/tools area without changing the existing Windows, Linux, or Flash player instructions; verify the relative links resolve from `README.md`.

## 3. Verify documentation integrity and scope

- [x] 3.1 Run static checks that every referenced repository path exists, required baseline topics are present, internal Markdown links resolve, `legacy-baseline` still resolves to `e8c98a03c902eba70323538dc5d4eaba2f2927a1`, and `git diff --check` passes; inspect the diff and confirm no runtime, dependency, asset, save, configuration, or generated skill file changed.
