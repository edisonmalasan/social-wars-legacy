## Context

See `proposal.md` for motivation and `specs/legacy-save-fixtures/spec.md` for the behavioral contract. The repository has no tracked or local authentic player-save corpus: `saves/` is ignored and absent. `villages/initial.json` is the fresh-state template, while the other files under `villages/` are static neighbor or quest content and cannot establish player progression history.

The legacy path is small but stateful. Importing `sessions.py` loads the initial template; `sessions.new_village()` chooses a UUID, deep-copies the template, assigns player and timestamp fields, calls `version.migrate_loaded_save()`, stores the result in memory, and persists indented JSON beneath the imported `SAVES_DIR`. The baseline source identities are stable at preservation commit `e8c98a03c902eba70323538dc5d4eaba2f2927a1`.

## Goals / Non-Goals

**Goals:**

- Produce reproducible fresh-player and migration-boundary evidence through the actual legacy code path.
- Make the committed fixture bytes and their provenance independently checkable.
- Contain all capture side effects and make verification read-only with respect to repository evidence.
- State the limits of the available evidence prominently enough that later work cannot mistake static content for observed player history.

**Non-Goals:**

- Invent, synthesize, or infer progressed player histories.
- Modify legacy runtime behavior, dependencies, content, or save serialization.
- Capture protocol traffic, execute Flash, or start canonical-save migration design.
- Generalize the tool into a broad fixture framework before another preservation slice needs it.

## Decisions

### Exercise legacy modules under controlled process state

The capture command will run from the repository root, validate the required legacy source blobs against the recorded baseline commit, and invoke the imported legacy creation and migration behavior with a fixed UUID and timestamp. It will redirect the `sessions` module's already-imported save location to a temporary directory and isolate its in-memory state for the command lifetime.

This retains the behavior under preservation instead of duplicating it in a fixture builder. Copying or reimplementing `new_village()` was rejected because such a generator could remain stable while the legacy path drifted.

### Capture both sides of the migration boundary

The pre-migration fixture will be assembled from the verified initial template using the same deep-copy and field assignments performed immediately before `migrate_loaded_save()`. The post-migration fixture will be the exact file persisted by the controlled `new_village()` run. A full-object comparison will prove that migrating the pre-state yields the post-state.

An assertion over a small set of known migrated fields was rejected because it would silently ignore changes to unknown or newly discovered legacy fields.

### Use deterministic repository fixtures plus a manifest

Canonical JSON bytes will follow the legacy persisted representation where applicable. A deterministic manifest will record fixture paths, roles, byte sizes, SHA-256 digests, fixed UUID/time values, baseline commit, and Git blob IDs for `villages/initial.json`, `sessions.py`, `version.py`, and `bundle.py`. Entries will also classify what is verified and what is unavailable.

Recording only the current commit was rejected because later documentation or tooling commits would obscure which preserved legacy source bytes were actually used. Blob identities let verification distinguish harmless repository progress from source drift.

### Separate generation from verification

Generation may replace only the named canonical fixture outputs after successful capture and validation. Verification will generate into temporary storage, compare exact bytes and manifest facts, and never rewrite canonical files. Both modes will fail with actionable paths and non-zero exit status on drift.

A single command that silently refreshes fixtures was rejected because it would turn review-time drift into an accepted baseline.

### Keep the implementation dependency-free and non-runtime

The tool and tests will use the Python standard library and the already verified CPython 3.9 legacy environment. They will require neither the server nor network, browser, or Flash execution. The tooling will live outside application runtime modules and will not change imports or behavior used by `server.py`.

## Risks / Trade-offs

- **[Import-time state or cwd assumptions could leak writes]** → Run with a verified repository cwd, redirect the module-level save path before invoking persistence, snapshot relevant paths, and test that no repository runtime save appears.
- **[A controlled fixture may be mistaken for captured historical play]** → Record `controlled` provenance and explicit unavailable progression categories in both manifest and human documentation.
- **[Legacy source drift can make regeneration impossible from the working tree]** → Fail verification against baseline blob identities rather than quietly accepting new output; a future approved change can deliberately establish a new evidence version.
- **[Exact JSON bytes can be platform-sensitive]** → Define serialization and newline expectations explicitly and test repeat generation in the supported Windows x64 CPython 3.9 baseline.
- **[Only the fresh state is available]** → Treat this as one bounded preservation slice; authentic early/mid/late/stress evidence remains a roadmap gap rather than being fabricated.

## Migration Plan

1. Add the capture/verification command and focused tests without touching runtime modules.
2. Generate the canonical fixture set from the recorded baseline source identities.
3. Verify deterministic bytes, full-state migration, manifest integrity, and write containment.
4. Document commands and evidence limits only after they execute successfully.

Rollback consists of removing the new tool, tests, fixtures, and their documentation links. No application data or runtime migration is performed.
