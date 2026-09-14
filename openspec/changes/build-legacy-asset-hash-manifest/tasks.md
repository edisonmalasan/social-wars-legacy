## 1. Build the Git-blob corpus reader

- [x] 1.1 Add the Python 3.9-compatible `tools/hash-manifest/hash_manifest.py` CLI with local repository/ref resolution, NUL-safe tree enumeration, one streamed Git batch, exact blob hashing, explicit subprocess/protocol errors, and no shell or network invocation; verify focused tests cover binary blobs, truncated/error responses, missing refs, and Git failures.
- [x] 1.2 Implement the fixed nine-extension selection and fail-closed validation for regular blobs, UTF-8 repository-relative paths, traversal/absolute paths, case-insensitive collisions, and empty selections; verify tests cover every included suffix, excluded extensions and later/untracked files, spaces, mixed case, duplicates, unsafe paths, symlinks, and gitlinks.

## 2. Generate and verify the canonical manifest

- [x] 2.1 Implement schema version `1`, algorithm `sha256`, source kind/commit, policy `legacy-assets-v1`, fixed entry fields, exact-path ordering, canonical UTF-8 JSON serialization, atomic generation, protected output placement, and the specified `0`/`1`/`2` exit semantics; verify deterministic and schema-focused tests pass.
- [x] 2.2 Implement strictly read-only verification that reconstructs the recorded Git-blob corpus and compares source, paths, order, digests, sizes, and canonical bytes without regeneration; verify tests detect added, removed, reordered, renamed, digest/size-tampered, malformed, unsupported, and unavailable-source manifests while leaving inputs unchanged.

## 3. Record the immutable baseline evidence

- [x] 3.1 Add a narrow `.gitattributes` LF rule for `legacy-manifest.json`, generate the manifest twice from `legacy-baseline`, and verify byte-for-byte identical output, full commit `e8c98a03c902eba70323538dc5d4eaba2f2927a1`, exactly 3,258 entries, canonical structure, and successful read-only verification.
- [x] 3.2 Independently enumerate the baseline selection and cross-check its complete path set plus representative SHA-256/size values against raw Git blobs; verify Git status/diff show no preserved asset, configuration, village, mod, template, stub, tool input, save, or runtime source change.

## 4. Document and accept the preservation tool

- [x] 4.1 Add focused tool documentation and update `README.md`, `docs/legacy-baseline.md`, and `AGENTS.md` only with commands actually executed successfully, recording the immutable source, policy, entry count, evidence, exit behavior, Git/Python prerequisites, and all excluded integrity/provenance/runtime/save claims; verify links and commands from the repository root.
- [ ] 4.2 Inspect the final diff against every proposal/design/spec requirement, run the focused automated tests, full-corpus generate/verify/determinism and independent cross-checks, `git diff --check`, installed OpenSpec implementation verification, and `openspec validate build-legacy-asset-hash-manifest --strict`, treating every CRITICAL or WARNING finding as blocking before acceptance.
