## 1. Strict Input and Comparison Core

- [ ] 1.1 Implement Python 3.9-compatible strict JSON loading for explicit state-pair and recorder-v1 modes, including mutual exclusion, object-boundary validation, duplicate/non-finite rejection, and 16 MiB input limits; verify focused CLI tests cover valid modes, unavailable boundaries, invalid schemas/types/UTF-8/JSON, duplicate keys, non-finite values, and no hidden file discovery.
- [ ] 1.2 Implement type-strict structural traversal with exact case-sensitive keys, positional arrays, RFC 6901 paths, subtree-root additions/removals, and the specified depth/node/change limits; verify focused tests cover canonical `/version`, unknown fields, empty containers, missing versus null, bool/integer/number distinctions, key escaping, array mutations, and every limit.

## 2. Safe Deterministic Reporting

- [ ] 2.1 Implement the value-free schema-version-1 report, deterministic ordering/serialization, and exit statuses `0`, `1`, and `2`; verify repeated semantically equivalent inputs produce byte-identical output and all failures emit no partial success report.
- [ ] 2.2 Implement compatible sensitive-value collection and path-component protection with explicit collision rejection plus bounded categorical diagnostics; verify supplied secrets never occur in stdout/stderr, changed secret-bearing paths remain detectable, collisions fail, and raw exception/path/key/value text is absent.

## 3. Containment and Documentation

- [ ] 3.1 Add complete focused tests proving both success and failure leave supplied files, canonical fixtures, runtime saves, repository sources, and surrounding directories byte-identical and create no cache, bytecode, temp report, server, network, browser, or Flash activity.
- [ ] 3.2 Document the successfully executed commands, input modes, report schema, ordering/type semantics, limits, exit statuses, recorder boundary meaning, privacy limitations, containment guarantees, and explicit exclusions; add repository guidance/linkage only for commands actually run and verify all local links resolve.

## 4. Final Verification

- [ ] 4.1 Run the focused state-diff suite with the verified Windows x64 CPython 3.9.13 environment, both preservation verifier/test suites, recorder tests, `python -m pip --isolated check`, contained `python -m compileall -q .`, strict OpenSpec validation, documentation-link checks, and independent implementation-versus-artifact verification; inspect the complete diff/status and report any unavailable check exactly.
