## Context

Recorder-v1 files contain sanitized parsed command envelopes and complete in-memory boundaries around `command()`. They do not contain a server-clock call stream or immutable historical source provenance. The legacy dispatcher applies resource deltas before command-specific logic, calls `timestamp_now()` for every command, saves once after a successful batch, and can leave unsaved partial memory after an exception. `server.py` has startup and network-adjacent side effects and is not an acceptable replay import. The existing state-diff core already defines strict, value-free complete-structure comparison.

## Goals / Non-Goals

**Goals:**

- Reproduce the strongest currently evidenced clock-independent success and partial-failure transactions using the actual legacy dispatcher.
- Make legacy execution disposable, source-pinned, bounded, and incapable of reading or writing repository runtime saves.
- Reuse the durable state-diff policy and report mismatch evidence without disclosing payload values.

**Non-Goals:**

- General command replay, recorded clock/RNG reconstruction, HTTP/signature/session replay, or historical-source attestation.
- Fixture capture/promotion, catalogs, domain normalization, patch application, server startup, or modern runtime work.

## Decisions

### Allowlist four clock-independent command branches

The first slice supports `complete_tutorial`, `level_up`, `ping`, and `set_variables`. These cover mutation, ordering, resource application and the repository's genuine `IndexError` partial-failure evidence without making state depend on the unconditional clock call. Per-command argument validation keeps the execution surface bounded while preserving the known empty-argument failure case.

Alternative: replay every recorded command and ignore time-dependent paths. Rejected because the recorder did not capture legacy clock inputs, and ignore rules would weaken complete-state evidence.

### Pin the minimal oracle closure to the preservation baseline

An implementation-owned manifest records baseline `e8c98a03c902eba70323538dc5d4eaba2f2927a1` blobs for the dispatcher import closure and consumed config/mod content. Current repository evidence confirms that closure is unchanged. The parent verifies regular, unlinked checkout files against local immutable blobs with Git network/fetch disabled, then copies only reviewed files to an external temporary source root.

Alternative: copy the whole current checkout or trust mutable `HEAD`. Rejected because either widens the child surface or loses a stable oracle identity.

### Run the original dispatcher in an isolated child

The parent strictly validates the record without importing legacy modules. It starts a `-I -B` child with a minimal environment and 30-second timeout. The child imports only the copied closure, redirects `sessions.SAVES_DIR`, seeds `sessions.__saves` under a fixed internal alias while preserving state contents, replaces the dispatcher-visible clock with a sentinel, captures legacy stdout/stderr, executes `command()`, and returns a bounded internal result. `server.py`, loaders, migration, recorder observation, and live services are never invoked.

Alternative: monkeypatch legacy modules in the parent. Rejected because imports consume configuration and global state and would weaken process cleanup and timeout boundaries.

### Normalize only the evidenced outcome boundary

Eligible success records must describe recorder success, null error, and the fixed route response. The only eligible failure describes command-phase `IndexError`, null body and status 500. Other exceptions are categorical replay failures, not comparable outcomes. Success must create a disposable persisted state identical to memory; the supported failure must create no save.

Alternative: treat arbitrary recorded exceptions as replayable. Rejected because their phases, Flask behavior and nondeterministic dependencies are not currently evidenced.

### Reuse structural comparison with combined secret collection

The parent loads the state-diff module as tool code and uses its strict JSON/type/path/change policy. Before rendering changes it collects known-sensitive values from both the complete record and actual replay result, so replay-created sensitive path components are protected too. Existing state-diff files and public behavior remain unchanged.

Alternative: duplicate the diff walker. Rejected because duplicated ordering, type and privacy semantics would drift.

### Publish one value-free aggregate report

The report nests the state-diff result and includes only categorical outcome, response and persistence equality. It is assembled and serialized before stdout begins. Exit `0` means every boundary matches, `1` means execution completed but at least one boundary differs, and `2` means no trustworthy comparison completed.

Alternative: include actual/expected values for diagnosis. Rejected because records remain private and may contain unidentified player data.

## Risks / Trade-offs

- [The four-command slice is not general replay] → Reject every other name explicitly and expand only when deterministic inputs and evidence exist.
- [Pinned sources prove replay code, not historical capture code] → Label provenance honestly and do not promote unknown records automatically.
- [Recorder sanitization is lossy] → Reject redaction in execution-relevant values and classify accepted sanitized state comparison narrowly.
- [A fixed sentinel is not recorded time] → Test supported results with two sentinels and reject any command whose state depends on it.
- [Temporary process containment is not an OS security sandbox] → Minimize and pin the closure, isolate environment/storage, forbid services, bound output/time, and document residual crash/race limits.
- [A pipe can fail after receiving an output prefix] → Serialize before writing and treat exit `2` as authoritative; shell redirection remains outside tool containment.

## Migration Plan

Add the tool, manifest, focused tests and documentation without changing legacy entry points. Rollback removes only these additions and their documentation links; recorder evidence, canonical fixtures, legacy sources and runtime saves remain untouched.
