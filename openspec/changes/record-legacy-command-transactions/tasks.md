## 1. Recorder Core

- [x] 1.1 Add a Python 3.9-compatible standard-library recorder module with disabled-by-default configuration, repository-boundary validation, versioned record construction, recursive sensitive-key sanitization, and bounded non-secret error metadata; verify focused tests reject unsafe destinations and find none of the supplied secret values in serialized records.
- [x] 1.2 Implement collision-safe per-request JSON persistence through an atomic same-directory replacement; verify multiple controlled writes create distinct complete records, leave no temporary files, and touch only the configured external directory.

## 2. Legacy Command Integration

- [x] 2.1 Integrate observation around the existing `command.php` parse, `command()`, persistence, and response boundary without changing their order; verify successful and failing controlled requests record the available complete before/after states, sanitized parsed commands, response or error outcome, status, duration, and correlation fields.
- [x] 2.2 Keep recorder snapshot, serialization, persistence, and diagnostic failures fail-open while visible; verify forced recorder failures preserve the original response or exception and produce the same resulting player-save bytes as recording-disabled execution.

## 3. Verification and Documentation

- [x] 3.1 Add focused tests for disabled transparency, enabled success, parse/command failure, complete state boundaries, credential exclusion, unsafe configuration, atomicity, collision safety, and write containment; run them successfully with the verified Windows x64 CPython 3.9.13 environment.
- [x] 3.2 Document the successfully executed enablement and test commands, external-directory requirement, record schema, sanitization policy, failure semantics, privacy limitations, and explicit exclusions; update repository command guidance only with commands actually executed successfully and verify documentation links resolve.

## 4. Final Verification

- [x] 4.1 Run the focused recorder tests, existing save-fixture and asset-manifest verification/tests, `python -m pip --isolated check`, the contained `python -m compileall -q .` baseline check, strict OpenSpec validation, and the installed OpenSpec implementation verification workflow; inspect `git diff` and `git status` and report any unavailable check exactly.
