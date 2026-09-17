## 1. Strict Evidence and Oracle Provenance

- [x] 1.1 Implement Python 3.9-compatible strict recorder-v1 loading and eligibility validation for the explicit four-command slice, coherent boundaries/outcome/response metadata, exact argument/resource shapes, redaction rejection, and input/depth/node/batch limits; verify focused tests cover every accepted and rejected form before legacy execution.
- [x] 1.2 Add the reviewed baseline oracle manifest and local immutable Git-blob verification for the minimal source/config/mod closure, rejecting missing, linked, extra configured, or drifted inputs without network or fetch; verify clean and adversarial provenance cases including CRLF/LF tolerance.

## 2. Contained Legacy Execution

- [x] 2.1 Implement the isolated `-I -B` disposable child with minimal environment, safe player alias, seeded before-state, redirected save path, captured legacy sinks, fixed sentinel clock, 30-second timeout, and 32 MiB result bound; verify it never imports server/recorder, discovers ambient saves, starts services, or writes outside disposable storage.
- [x] 2.2 Execute the original dispatcher for eligible batches and normalize success or the supported command-phase `IndexError`, preserving command order, resource-before-branch behavior, partial failure, trailing-command suppression, and success/failure persistence semantics; verify both sentinels produce identical supported results.

## 3. Comparison and Private Reporting

- [x] 3.1 Reuse the state-diff core for complete expected-versus-actual state comparison with combined record/actual sensitive-value collection and collision rejection; verify strict types, exact paths, unknown-field preservation, change limits, replay-created secret protection, and no duplicated comparison policy.
- [x] 3.2 Implement the deterministic value-free `legacy-command-replay-v1` aggregate report and exit statuses `0`, `1`, and `2`; verify state, outcome, response, and persistence matches/mismatches, repeated byte identity, categorical diagnostics, serialization/output failures, and absence of values or legacy output.

## 4. Containment, Documentation, and Final Verification

- [x] 4.1 Add complete focused tests proving success, difference, supported exception, invalid evidence, provenance drift, timeout/crash/dependency/persistence/output failure, and cleanup leave supplied evidence, repository/runtime/canonical/recorder paths, sources, and surrounding files byte-identical with no cache, bytecode, report, process, network, browser, server, or Flash activity.
- [x] 4.2 Document only successfully executed commands, supported record/command shapes, oracle provenance, comparison/report semantics, limits, exit statuses, privacy and sanitization limits, containment guarantees, persistence meaning, evidence classification, and exclusions; then run the replay suite on verified Windows x64 CPython 3.9.13, existing preservation suites/verifiers, package consistency, contained compileall, strict OpenSpec validation, link checks, full diff/status review, and independent implementation-versus-artifact verification.
