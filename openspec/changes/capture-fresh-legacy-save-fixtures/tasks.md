## 1. Capture Tooling

- [ ] 1.1 Add a Python 3.9-compatible standard-library fixture command that validates the recorded baseline commit and Git blob identities before capture; verify it rejects a mismatched legacy source with an actionable non-zero result.
- [ ] 1.2 Implement controlled fresh-player capture through the actual legacy `sessions.new_village()` persistence path using fixed UUID/time inputs and a disposable save location; verify repeated captures are byte-identical and leave the repository `saves/` path unchanged.
- [ ] 1.3 Capture the complete controlled pre-migration state and verify the actual legacy migration produces the complete persisted post-migration state without dropping unknown fields.

## 2. Canonical Evidence

- [ ] 2.1 Implement deterministic generation of only the approved canonical fixture paths and a manifest containing roles, classifications, SHA-256 digests, byte sizes, controlled inputs, baseline commit, and source blob IDs; verify two generations produce identical files.
- [ ] 2.2 Implement read-only verification that regenerates in temporary storage and detects fixture, manifest, provenance, or source drift with concrete non-zero diagnostics; verify canonical files retain their original bytes.
- [ ] 2.3 Generate and review the committed pre-migration fixture, persisted fresh-player/post-migration fixture, and manifest evidence; verify manifest hashes and sizes independently against every committed fixture.

## 3. Tests and Documentation

- [ ] 3.1 Add focused tests for actual-path capture, full-state migration, deterministic regeneration, tamper detection, source-provenance rejection, and write containment; run them successfully in the verified legacy Python environment.
- [ ] 3.2 Document the successfully executed generation and verification commands, provenance model, and evidence classification; explicitly mark early-, mid-, late-game, and stress-town player saves unavailable/unverified and static neighbors as non-player fixtures, then verify repository documentation links resolve.

## 4. Final Verification

- [ ] 4.1 Run the focused fixture tests, read-only fixture verification, `python -m pip --isolated check`, the contained `python -m compileall -q .` baseline check, strict OpenSpec validation, and the installed OpenSpec implementation verification workflow; inspect `git diff` and `git status` and report any unavailable check exactly.
