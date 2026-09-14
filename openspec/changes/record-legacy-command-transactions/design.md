## Context

See `proposal.md` for motivation. The current Flask `command.php` route reads form values, separates a 64-character signature from a JSON payload, parses that payload, calls `command(USERID, data)`, and then returns a fixed success object. `command()` mutates the in-memory save and calls `save_session()` once after processing the batch. There is no request middleware, protocol evidence schema, or automated gameplay test framework, while controlled save fixtures and a verified CPython 3.9 environment now exist.

## Goals / Non-Goals

**Goals:**

- Observe one high-value mutation boundary without changing its response, exception, mutation, or save behavior.
- Produce self-contained transaction records with complete before/after state and enough request/response context for later golden-fixture review.
- Make disabled mode inert and enabled writes explicit, external to the repository, atomic, collision-safe, and testable.
- Exclude authentication-bearing values before serialization and diagnose recorder failures without masking legacy behavior.

**Non-Goals:**

- General Flask middleware or coverage of login, configuration, player-info, alliance, static, or error-tracking routes.
- Replay, generalized state diff, command/endpoint catalogs, canonicalization of captured records, or automatic commits.
- Validation or correction of the legacy signature, authorization, resource trust, command semantics, or save format.
- Flash/browser execution, dependency changes, progressed-save fabrication, or modernization of the legacy server.

## Decisions

### Instrument the route around the existing call boundary

The route will delegate observation to a small recorder module while retaining the existing parse, `command()`, and response order. It will deep-copy the complete player state immediately before command execution and again after success or failure. This keeps observation adjacent to the only currently persisted command boundary and avoids modifying the large dispatcher.

Alternative: Flask-wide before/after hooks. Rejected for this slice because they cannot naturally capture the parsed command batch or exact mutation boundary and would silently broaden scope to every route.

### Configure an external evidence directory and remain disabled by default

A single documented environment variable will enable recording only when its resolved destination is outside the repository root. The module will validate this boundary before a request is recorded. Tests will use a disposable temporary directory.

Alternative: an ignored directory inside the checkout. Rejected because ignored evidence can still mix with preserved source and can be accidentally force-added; an external destination gives a stronger containment guarantee.

### Use versioned one-record JSON files with atomic replacement

Each request will build an in-memory schema-versioned object and write UTF-8 JSON through a uniquely named temporary file in the destination before an atomic same-directory replacement. Collision-resistant record IDs and filenames allow concurrent or rapid requests without overwriting evidence. Stable key ordering makes controlled records comparable, while timestamps, durations, and record IDs remain explicitly observational rather than deterministic fixture values.

Alternative: append-only JSON Lines. Rejected because concurrent appends and interrupted writes make isolation and partial-record detection harder in the current single-file legacy architecture.

### Sanitize structured data before serialization

The route will not record the raw combined `data` form value or its 64-character signature. A recursive sanitizer will replace configured sensitive keys case-insensitively in form metadata, headers, cookies, and parsed payloads; only an allowlisted subset of HTTP headers will be considered. Errors will be represented by type and bounded diagnostic text, not tracebacks or request dumps.

Alternative: encrypt complete raw requests. Rejected because it introduces key management and dependencies while still retaining secrets that are unnecessary for behavioral replay.

### Keep recorder failures fail-open and visible

Snapshot or persistence failures will emit an actionable diagnostic through the existing process logging path, then return or re-raise the original legacy outcome unchanged. Tests will compare disabled, enabled, and forced-recorder-failure results and save bytes.

Alternative: fail the HTTP request when evidence cannot be written. Rejected because instrumentation would change the behavioral oracle.

## Risks / Trade-offs

- [Deep-copy cost increases command latency while recording] → Keep recording opt-in, measure duration around legacy execution separately from evidence persistence, and document that capture mode is diagnostic rather than production operation.
- [A process exit can occur after mutation but before record persistence] → Atomic files prevent corrupt records, but absence of evidence remains possible and is documented rather than changing legacy transaction semantics.
- [Complete state can include player-associated data] → Require an external operator-controlled destination, never auto-promote records to fixtures, and keep credential sanitization independent of later evidence review.
- [Recorder diagnostics can themselves fail] → Use a minimal standard-library diagnostic path and never let diagnostic errors replace the legacy result.
- [The current command path trusts client-supplied resource deltas] → Record the observed values unchanged and leave security remediation to a later specified change.

## Migration Plan

1. Add the isolated recorder module and focused unit/integration tests without enabling it by default.
2. Integrate the `command.php` route at the existing parse/execute/respond boundary.
3. Verify controlled requests with recording disabled, enabled, failed, and persistence-failure modes against identical resulting save bytes and HTTP behavior.
4. Document enablement, external-directory containment, schema, sanitization, and limitations.
5. Roll back by removing the environment setting; disabled mode performs no recorder writes and requires no evidence migration.
